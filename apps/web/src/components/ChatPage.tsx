/** 对话工作台（web-chat-publish：SSE 流式 + 内联问题卡片）。
 *  SSE 消费参考: Easel api.ts streamChat（ReadableStream 手解帧）。 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { Approval } from "../lib/api";
import { answerQuestion, createChatSession, fetchApprovals, fetchChatSessions } from "../lib/api";
import { IconSend } from "./icons";

interface Msg {
  role: "user" | "assistant";
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

export default function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [current, setCurrent] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [interrupt, setInterrupt] = useState<InterruptCard | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [input, setInput] = useState("");
  const [toast, setToast] = useState<{ text: string; ok: boolean } | null>(null);
  const streamAbort = useRef<AbortController | null>(null);

  const showToast = (text: string, ok = true) => {
    setToast({ text, ok });
    setTimeout(() => setToast(null), 2200);
  };

  const loadSessions = useCallback(async () => {
    try {
      const list = await fetchChatSessions();
      setSessions(list);
    } catch {
      setSessions([]);
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const loadHistory = useCallback(async (threadId: string) => {
    try {
      const r = await fetch(`/api/chat/sessions/${threadId}/messages`);
      if (!r.ok) return;
      const body = await r.json();
      setMessages(body.messages || []);
    } catch {
      /* 历史读取失败保持本地流 */
    }
  }, []);

  // W4：切换会话/卸载时中止进行中的流
  useEffect(() => {
    return () => streamAbort.current?.abort();
  }, []);

  const switchSession = (s: Session) => {
    streamAbort.current?.abort();
    setPhase("idle");
    setCurrent(s);
    setInterrupt(null);
    void loadHistory(s.thread_id);
  };

  const newSession = async () => {
    try {
      const s = await createChatSession("xhs-main", "新对话");
      await loadSessions();
      setCurrent(s);
      setMessages([]);
      setInterrupt(null);
    } catch (e) {
      showToast(e instanceof Error ? e.message : String(e), false);
    }
  };

  /** SSE 消费：解析 event/data 帧，token 拼接进当前 assistant 气泡。 */
  const runStream = async (threadId: string, message: string) => {
    setPhase("streaming");
    setMessages((m) => [...m, { role: "user", content: message }, { role: "assistant", content: "" }]);
    streamAbort.current = new AbortController();
    try {
      const res = await fetch(`/api/chat/sessions/${threadId}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
        signal: streamAbort.current.signal,
      });
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
          const payload = JSON.parse(dataLine.slice(6));
          if (event === "token") {
            setMessages((m) => {
              const last = m[m.length - 1];
              if (last?.role === "assistant") {
                return [...m.slice(0, -1), { ...last, content: last.content + payload.text }];
              }
              return [...m, { role: "assistant", content: payload.text }];
            });
          } else if (event === "interrupt") {
            setInterrupt({ thread_id: threadId, isQuestion: false });
            // 问题载荷来自 pending 接口（interrupt 帧后拉取）
            const pending = await fetchApprovals().catch(() => [] as Approval[]);
            const mine = pending.find((p) => p.thread_id === threadId);
            if (mine?.kind === "question") {
              setInterrupt({ thread_id: threadId, question: mine.question, options: mine.options, isQuestion: true });
            } else if (mine) {
              setInterrupt({ thread_id: threadId, isQuestion: false });
            }
          } else if (event === "error") {
            showToast(payload.message, false);
          }
        }
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) {
        showToast(e instanceof Error ? e.message : String(e), false);
      }
    } finally {
      setPhase("idle");
      streamAbort.current = null;
    }
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
            在对话中驱动 agent（选题→创作→审批）；命中人工闸门时出现卡片，回答后续跑
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
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "chat-msg user" : "chat-msg"}>
              {m.content}
            </div>
          ))}
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
                    onClick={() => void answerQuestion(interrupt.thread_id, o).then(() => setInterrupt(null))}
                  >
                    {o}
                  </button>
                ))}
                <a className="btn btn-sm" href="#/approvals">
                  前往审批中心
                </a>
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
