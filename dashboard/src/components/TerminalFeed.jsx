export default function TerminalFeed() {

  const logs = [
    "[ topology ] graph synchronization complete",
    "[ anomaly ] fan-out structure detected",
    "[ risk ] propagation index elevated",
    "[ engine ] transaction matrix updated",
    "[ graph ] laundering cluster identified"
  ];

  return (
    <div
      style={{
        position: "absolute",
        top: 30,
        right: 30,
        width: 420,
        padding: 20,
        border: "1px solid #161616",
        background: "rgba(0,0,0,0.7)"
      }}
    >
      <div
        style={{
          fontSize: 10,
          letterSpacing: "0.14em",
          color: "#444",
          marginBottom: 16
        }}
      >
        TERMINAL STREAM
      </div>

      {logs.map((log, i) => (
        <div
          key={i}
          style={{
            color: "#777",
            fontSize: 11,
            padding: "8px 0",
            borderBottom: "1px solid #111"
          }}
        >
          {log}
        </div>
      ))}
    </div>
  );
}
