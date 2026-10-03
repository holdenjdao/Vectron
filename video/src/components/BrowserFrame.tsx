import { ui } from "../content";
import { colors, fonts, shadow } from "../theme";

export const CHROME_HEIGHT = 44;

interface Props {
  /** Width of the page area in px; the 1440×900 app is scaled to fit. */
  width: number;
  url: string;
  children: React.ReactNode;
}

/**
 * A quiet browser window. Children are laid out in the app's own 1440×900
 * CSS-pixel space, so screenshots and highlights line up exactly.
 */
export const BrowserFrame: React.FC<Props> = ({ width, url, children }) => {
  const scale = width / ui.viewport.width;
  return (
    <div
      style={{
        width,
        borderRadius: 16,
        overflow: "hidden",
        background: colors.bgRaised,
        border: "1px solid rgba(255,255,255,0.10)",
        boxShadow: shadow,
      }}
    >
      <div
        style={{
          height: CHROME_HEIGHT,
          display: "flex",
          alignItems: "center",
          padding: "0 18px",
          gap: 9,
          background: "#16181f",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span key={i} style={{ width: 12, height: 12, borderRadius: 6, background: "rgba(255,255,255,0.16)" }} />
        ))}
        <div
          style={{
            margin: "0 auto",
            padding: "5px 22px",
            borderRadius: 8,
            background: "rgba(255,255,255,0.05)",
            color: colors.dim,
            fontFamily: fonts.mono,
            fontSize: 15,
            letterSpacing: "0.02em",
          }}
        >
          {url}
        </div>
        <span style={{ width: 54 }} />
      </div>
      <div style={{ width, height: ui.viewport.height * scale, position: "relative", overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            width: ui.viewport.width,
            height: ui.viewport.height,
            transform: `scale(${scale})`,
            transformOrigin: "0 0",
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
};
