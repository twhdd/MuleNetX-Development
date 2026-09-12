export default function EventFeed() {

  const events = [
    "ACC-8842 connected to KNOWN-BAD",
    "Layering ring anomaly detected",
    "Topology graph updated",
    "Risk propagation increased",
    "Velocity spike detected",
    "Suspicious flow cluster found"
  ];

  return (
    <div
      style={{
        position: "absolute",
        bottom: 30,
        left: 30,

        width: 420,

        padding: 20,

        border: "1px solid #161616",

        background: "rgba(0,0,0,0.7)"
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "#444",

          letterSpacing: "0.14em",

          marginBottom: 16
        }}
      >
        LIVE EVENT STREAM
      </div>

      {events.map((event, i) => (

        <div
          key={i}

          style={{
            padding: "8px 0",

            borderBottom: "1px solid #111",

            color: "#666",

            fontSize: 11
          }}
        >
          &gt; {event}
        </div>
      ))}
    </div>
  );
}
