import { ImageResponse } from "next/og"

export const alt = "AION, the Guide Between Worlds"
export const size = { width: 1200, height: 630 }
export const contentType = "image/png"

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "72px 88px",
          color: "#f2f6ff",
          background:
            "radial-gradient(circle at 22% 42%, #124c9b 0%, #071a38 26%, transparent 48%), radial-gradient(circle at 80% 18%, #39206f 0%, transparent 38%), #030914",
        }}
      >
        <div style={{ display: "flex", width: 410, height: 410, alignItems: "center", justifyContent: "center", border: "2px solid #2bd6ff66", borderRadius: 205 }}>
          <div style={{ display: "flex", width: 330, height: 330, position: "relative", alignItems: "center", justifyContent: "center" }}>
            <div style={{ position: "absolute", left: 0, width: 110, height: 190, borderRadius: 70, background: "linear-gradient(135deg,#df77d7,#7144a5)" }} />
            <div style={{ position: "absolute", right: 0, width: 110, height: 190, borderRadius: 70, background: "linear-gradient(135deg,#df77d7,#7144a5)" }} />
            <div style={{ display: "flex", width: 230, height: 292, borderRadius: "48%", background: "linear-gradient(135deg,#27a9ff,#173a9d)", position: "relative", alignItems: "center", justifyContent: "center" }}>
              <div style={{ position: "absolute", top: -8, left: 18, width: 194, height: 74, borderRadius: 50, background: "radial-gradient(circle,#285ee8 0 36%,#143ea7 40%)" }} />
              <div style={{ display: "flex", gap: 34, marginTop: -26 }}>
                <div style={{ width: 52, height: 52, borderRadius: 26, background: "#12151d", border: "3px solid #697284" }} />
                <div style={{ width: 52, height: 52, borderRadius: 26, background: "#12151d", border: "3px solid #697284" }} />
              </div>
              <div style={{ position: "absolute", bottom: 52, width: 112, height: 46, borderRadius: "50%", background: "#ed72b4", borderTop: "2px solid #ffd1e8" }} />
            </div>
          </div>
        </div>
        <div style={{ display: "flex", width: 570, flexDirection: "column" }}>
          <div style={{ fontSize: 92, letterSpacing: 20, fontWeight: 300 }}>AION</div>
          <div style={{ marginTop: 12, fontSize: 26, color: "#81dcff", letterSpacing: 2 }}>ALCHEMICAL INTELLIGENCE FOR ONTOLOGICAL NAVIGATION</div>
          <div style={{ marginTop: 34, fontSize: 38, lineHeight: 1.25, fontWeight: 300 }}>The Guide who remembers who you are becoming.</div>
        </div>
      </div>
    ),
    size,
  )
}
