import { Img, staticFile } from "remotion";

import { colors, fonts, shadow, type } from "../theme";

interface Props {
  src: string;
  /** Natural pixel size of the image, so its proportions are kept. */
  natural: { width: number; height: number };
  width: number;
  label: string;
  /** Which corner the label chip sits in, to keep it off important detail. */
  labelAt?: "top" | "bottom";
  style?: React.CSSProperties;
}

/** A screenshot crop on a lifted card, labelled with a chip in its right-hand corner. */
export const Card: React.FC<Props> = ({ src, natural, width, label, labelAt = "top", style }) => {
  const height = (width * natural.height) / natural.width;
  return (
    <div
      style={{
        position: "absolute",
        width,
        height,
        borderRadius: 14,
        overflow: "hidden",
        border: "1px solid rgba(255,255,255,0.10)",
        boxShadow: shadow,
        background: colors.card,
        ...style,
      }}
    >
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", display: "block" }} />
      <div
        style={{
          position: "absolute",
          [labelAt]: 14,
          right: 14,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "8px 14px",
          borderRadius: 999,
          background: "rgba(11, 12, 16, 0.88)",
          border: `1px solid ${colors.line}`,
          fontFamily: fonts.mono,
          fontWeight: 500,
          fontSize: type.micro,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: colors.text,
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: 4, background: colors.accent }} />
        {label}
      </div>
    </div>
  );
};
