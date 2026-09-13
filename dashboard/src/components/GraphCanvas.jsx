import { useState } from "react";

import ForceGraph from "./ForceGraph";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export default function GraphCanvas() {

    const [account,setAccount] =
        useState("");

    const [graph,setGraph] =
        useState({
            nodes: [],
            links: []
        });

    async function loadGraph() {

        const response =
        await fetch(
            `${API_BASE_URL}/api/graph/network/${account}`
        );

        const data =
        await response.json();

        setGraph(data);
    }

    return (

        <div>

            <h2>
                Graph Explorer
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
                Explore
            </button>

            <ForceGraph
                data={graph}
            />

        </div>
    );
}
