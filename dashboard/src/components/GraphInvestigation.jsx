import { useState } from "react";

export default function GraphInvestigation() {

    const [account,setAccount] =
        useState("");

    const [nodes,setNodes] =
        useState([]);

    async function loadGraph() {

        const response =
        await fetch(
            `http://localhost:8000/api/graph/${account}`
        );

        const data =
        await response.json();

        setNodes(data);
    }

    return (

        <div>

            <h2>
                Investigation Graph
            </h2>

            <input
                value={account}
                onChange={(e)=>
                    setAccount(
                        e.target.value
                    )
                }
                placeholder="Account ID"
            />

            <button
                onClick={loadGraph}
            >
                Load
            </button>

            <pre>
                {
                    JSON.stringify(
                        nodes,
                        null,
                        2
                    )
                }
            </pre>

        </div>
    );
}
