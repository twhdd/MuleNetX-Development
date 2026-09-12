import { useState } from "react";

import ForceGraph from "./ForceGraph";


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
            `http://localhost:8000/api/graph/network/${account}`
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
