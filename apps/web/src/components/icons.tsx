/** 内联 SVG 图标——参考: Easel components/icons.tsx 模式（具名导出 IconXxx）。 */
import type { ComponentType } from "react";

type IconProps = { size?: number };

function base(size?: number) {
  return {
    width: size ?? 18,
    height: size ?? 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
}

export const IconDashboard: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <rect x="3" y="3" width="7" height="9" rx="1" />
    <rect x="14" y="3" width="7" height="5" rx="1" />
    <rect x="14" y="12" width="7" height="9" rx="1" />
    <rect x="3" y="16" width="7" height="5" rx="1" />
  </svg>
);

export const IconCheck: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

export const IconX: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M18 6L6 18M6 6l12 12" />
  </svg>
);

export const IconIdea: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M9 18h6M10 22h4" />
    <path d="M12 2a7 7 0 00-4 12.7c.6.5 1 1.4 1 2.3h6c0-.9.4-1.8 1-2.3A7 7 0 0012 2z" />
  </svg>
);

export const IconCalendar: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <rect x="3" y="4" width="18" height="18" rx="2" />
    <path d="M16 2v4M8 2v4M3 10h18" />
  </svg>
);

export const IconUser: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

export const IconTrend: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M23 6l-9.5 9.5-5-5L1 18" />
    <path d="M17 6h6v6" />
  </svg>
);

export const IconFolder: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
  </svg>
);

export const IconList: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
  </svg>
);

export const IconAlert: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    <path d="M12 9v4M12 17h.01" />
  </svg>
);

export const IconSend: ComponentType<IconProps> = ({ size }) => (
  <svg {...base(size)}>
    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
  </svg>
);
