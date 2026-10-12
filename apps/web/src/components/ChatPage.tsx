/** 对话工作台（feat-chat-resume-tools：SSE 流式 + 工具事件行 + 内联续跑）。
 *  SSE 消费参考: Easel api.ts streamChat（ReadableStream 手解帧）。 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { Approval } from "../lib/api";
import { createChatSession, fetchApprovals, fetchChatSessions, resumeChatStream } from "../lib/api";
import { IconSend } from "./icons";

interface Msg {
  role: "user" | "assistant" | "system";
  content: string;
}

interface Session {
  thread_id: string;
  account: string;
  title: string;
}

interface InterruptCard {
  thread_id: string;
  question?: string;
  options?: string[];
  isQuestion: boolean;
}

type Phase = "idle" | "streaming";

interface SsePayload {
  text?: string;
  message?: string;
  pending?: boolean;
  question?: string;
  options?: string[];
  tool?: string;
  status?: string;
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [current, setCurrent] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [interrupt, setInterrupt] = useState<InterruptCard | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [input, setInput] = useState("");
  const [toolLines, setToolLines] = useState<string[]>([]);
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);
  const streamAbort = useRef<AbortController | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const loadSessions = useCallback(async () => {
    setSessions(await fetchChatSessions().catch(() => []));
  }, []);

  useEffect(() => {
    void loadSessions();
    return () => streamAbort.current?.abort();
  }, [loadSessions]);

  const loadHistory = useCallback(async (threadId: string) => {
    try {
      const r = await fetch(`/api/chat/sessions/${threadId}/messages`);
      if (!r.ok) return;
      const body = await r.json();
      setMessages(body.messages || []);
    } catch {
      /* 历史读取失败保持本地 */
    }
  }, []);

  /** interrupt 帧后从 pending 拉取载荷（question/approval 两类卡片）。 */
  const handleInterruptFrame = useCallback(async (threadId: string) => {
    const pending = await fetchApprovals().catch(() => [] as Approval[]);
    const mine = pending.find((p) => p.thread_id === threadId);
    if (mine?.kind === "question") {
      setInterrupt({
        thread_id: threadId,
        question: mine.question,
        options: mine.options,
        isQuestion: true,
      });
    } else if (mine) {
      setInterrupt({ thread_id: threadId, isQuestion: false });
    }
  }, []);

  /** SSE 消费（D1/D2）：token/tool/interrupt/error/done 帧。 */
  const consumeSse = useCallback(
    async (threadId: string, res: Response) => {
      if (!res.ok || !res.body) throw new Error(`流请求失败 ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const frames = buf.split("\n\n");
        buf = frames.pop() || "";
        for (const frame of frames) {
          const evLine = frame.split("\n").find((l) => l.startsWith("event: "));
          const dataLine = frame.split("\n").find((l) => l.startsWith("data: "));
          if (!evLine || !dataLine) continue;
          const event = evLine.slice(7).trim();
          let payload: SsePayload;
          try {
            payload = JSON.parse(dataLine.slice(6));
          } catch {
            continue; // 单帧损坏跳过，不中断整条流
          }
          if (event === "token") {
            setMessages((m) => {
              const last = m[m.length - 1];
              if (last?.role === "assistant") {
                return [...m.slice(0, -1), { ...last, content: last.content + (payload.text ?? "") }];
              }
              return [...m, { role: "assistant", content: payload.text ?? "" }];
            });
          } else if (event === "tool") {
            const line = `⚙ ${payload.tool}（${payload.status}）`;
            setToolLines((l) => [...l.slice(-4), line]);
          } else if (event === "interrupt") {
            await handleInterruptFrame(threadId);
          } else if (event === "error") {
            showToast(payload.message ?? "流式请求失败", false);
          }
        }
      }
    },
    [handleInterruptFrame],
  );

  const runStream = async (threadId: string, message: string) => {
    setPhase("streaming");
    setToolLines([]);
    setMessages((m) => [...m, { role: "user", content: message }, { role: "assistant", content: "" }]);
    const myController = new AbortController();
    streamAbort.current = myController;
    try {
      const res = await fetch(`/api/chat/sessions/${threadId}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
        signal: myController.signal,
      });
      await consumeSse(threadId, res);
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        showToast(e instanceof Error ? e.message : String(e), false);
      }
    } finally {
      setPhase("idle");
      if (streamAbort.current?.signal === myController.signal) streamAbort.current = null;
    }
  };

  /** 断点续跑（D1）：决策构造收口后端，前端只传 kind+message。 */
  const resumeStream = async (threadId: string, kind: "question" | "approval" | "reject", message: string) => {
    setPhase("streaming");
    setToolLines([]);
    setInterrupt(null);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);
    const myController = new AbortController();
    streamAbort.current = myController;
    try {
      const res = await resumeChatStream(threadId, kind, message);
      await consumeSse(threadId, res);
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        showToast(e instanceof Error ? e.message : String(e), false);
      }
    } finally {
      setPhase("idle");
      if (streamAbort.current?.signal === myController.signal) streamAbort.current = null;
    }
  };

  const newSession = async () => {
    try {
      const s = await createChatSession("xhs-main", "新对话");
      await loadSessions();
      setCurrent(s);
      setMessages([]);
      setInterrupt(null);
      setToolLines([]);
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    }
  };

  const switchSession = (s: Session) => {
    streamAbort.current?.abort();
    setPhase("idle");
    setCurrent(s);
    setInterrupt(null);
    setToolLines([]);
    void loadHistory(s.thread_id);
  };

  const send = () => {
    if (!current || !input.trim() || phase === "streaming") return;
    const message = input.trim();
    setInput("");
    void runStream(current.thread_id, message);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="page-title">对话工作台</div>
          <div className="page-subtitle">
            在对话中驱动 agent（选题→创作→审批）；工具执行可见，闸门卡片内联处理
          </div>
        </div>
        <button className="btn btn-primary" onClick={() => void newSession()}>
          新对话
        </button>
      </div>
      <div className="chat-page">
        <div className="chat-sessions">
          {sessions.map((s) => (
            <button
              key={s.thread_id}
              className={current?.thread_id === s.thread_id ? "chip active" : "chip"}
              onClick={() => switchSession(s)}
            >
              {s.title}
            </button>
          ))}
        </div>
        <div className="chat-messages">
          {messages.map((m, i) =>
            m.role === "system" ? (
              <div key={i} className="page-subtitle">
                {m.content}
              </div>
            ) : (
              <div key={i} className={m.role === "user" ? "chat-msg user" : "chat-msg"}>
                {m.content}
              </div>
            ),
          )}
          {toolLines.length > 0 && (
            <div className="chat-msg page-subtitle">{toolLines[toolLines.length - 1]}</div>
          )}
          {interrupt && current && (
            <div className="card question" style={{ padding: 14, margin: "10px 0" }}>
              <div className="idea-card-title">
                {interrupt.isQuestion ? interrupt.question || "agent 有问题需要回答" : "需要你的确认"}
              </div>
              <div className="options">
                {(interrupt.options || []).map((o) => (
                  <button
                    key={o}
                    className="btn btn-sm"
                    disabled={phase === "streaming"}
                    onClick={() => void resumeStream(interrupt.thread_id, "question", o)}
                  >
                    {o}
                  </button>
                ))}
                {interrupt.isQuestion ? null : (
                  <>
                    <button
                      className="btn btn-sm btn-primary"
                      disabled={phase === "streaming"}
                      onClick={() => void resumeStream(interrupt.thread_id, "approval", "")}
                    >
                      确认
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      disabled={phase === "streaming"}
                      onClick={() => void resumeStream(interrupt.thread_id, "reject", "")}
                    >
                      拒绝
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
        <div className="chat-input">
          <input
            className="field"
            placeholder={current ? "输入消息…" : "先创建会话"}
            disabled={!current || phase === "streaming"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn btn-primary" disabled={!current || phase === "streaming"} onClick={send}>
            <IconSend size={15} />
          </button>
        </div>
      </div>
      {toast && <div className={toast.ok ? "toast ok" : "toast err"}>{toast.text}</div>}
    </>
  );
}
