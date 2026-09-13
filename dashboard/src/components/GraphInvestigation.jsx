import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export default function GraphInvestigation() {

    const [account,setAccount] =
        useState("");

    const [nodes,setNodes] =
        useState([]);

    async function loadGraph() {

        const response =
        await fetch(
            `${API_BASE_URL}/api/graph/${account}`
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
