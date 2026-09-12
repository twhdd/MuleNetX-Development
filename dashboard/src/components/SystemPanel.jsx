export default function SystemPanel() {

  const modules = [
    "GRAPH PROPAGATION ENGINE",
    "TOPOLOGY ANALYZER",
    "TRANSACTION INDEX",
    "FRAUD VECTOR SCANNER",
    "ANOMALY DETECTOR",
    "RISK MATRIX"
  ];

  return (
    <div
      style={{
        position: "absolute",
        top: 30,
        left: 30,
        width: 320,
        padding: 20,

        border: "1px solid #161616",

        background: "rgba(0,0,0,0.7)",

        backdropFilter: "blur(8px)"
      }}
    >
      <div
        style={{
          color: "#d8d8d8",
          fontSize: 24,
          marginBottom: 20,
          fontFamily: "Georgia"
        }}
      >
        MuleNetX
      </div>

      {modules.map((module, i) => (

        <div
          key={i}

          style={{
            display: "flex",
            justifyContent: "space-between",

            padding: "10px 0",

            borderBottom: "1px solid #111",

            fontSize: 10,
            letterSpacing: "0.12em",

            color: "#555"
          }}
        >
          <span>{module}</span>

          <span style={{ color: "#2e8b4e" }}>
            ONLINE
          </span>

        </div>
      ))}
    </div>
  );
}
