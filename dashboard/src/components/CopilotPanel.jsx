import { useState } from "react";

export default function CopilotPanel() {

    const [account, setAccount] = useState("");
    const [report, setReport] = useState("");

    async function investigate() {

        const response = await fetch(
            `http://localhost:8000/api/copilot/account/${account}`
        );

        const data = await response.json();

        setReport(
            data.report
        );
    }

    return (
        <div className="copilot-panel">

            <h2>MuleNetX Copilot</h2>

            <input
                value={account}
                onChange={(e) =>
                    setAccount(e.target.value)
                }
                placeholder="Account ID"
            />

            <button
                onClick={investigate}
            >
                Investigate
            </button>

            <pre>
                {report}
            </pre>

        </div>
    );
}
