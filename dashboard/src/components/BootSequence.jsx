import { useEffect, useState } from "react";

const lines = [
  "Initializing graph topology...",
  "Loading transaction matrices...",
  "Computing anomaly clusters...",
  "Scanning laundering patterns...",
  "Propagating risk vectors...",
  "MuleNetX online"
];

export default function BootSequence({ onComplete }) {
  const [visible, setVisible] = useState([]);

  useEffect(() => {
    lines.forEach((line, index) => {
      setTimeout(() => {
        setVisible(v => [...v, line]);
      }, index * 850);
    });

    setTimeout(() => {
      onComplete();
    }, lines.length * 850 + 400);

  }, []);

  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        background: "#000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}
    >
      <div
        style={{
          width: 700,
          fontFamily: "JetBrains Mono",
          fontSize: 13,
          color: "#8a8a8a",
          lineHeight: 2
        }}
      >
        {visible.map((line, i) => (
          <div key={i}>
            &gt; {line}
          </div>
        ))}
      </div>
    </div>
  );
}
