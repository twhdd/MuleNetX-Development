import { ForceGraph2D } from "react-force-graph";


export default function ForceGraph({
    data
}) {

    return (

        <div
            style={{
                width: "100%",
                height: "700px",
                border: "1px solid #222"
            }}
        >

            <ForceGraph2D

                graphData={data}

                nodeLabel={(node) =>
                    `
                    ${node.id}
                    Risk: ${node.risk}
                    Community: ${node.community}
                    `
                }

                nodeCanvasObject={(
                    node,
                    ctx,
                    globalScale
                ) => {

                    const label =
                        node.id;

                    const fontSize =
                        12 /
                        globalScale;

                    ctx.font =
                        `${fontSize}px Sans-Serif`;

                    ctx.beginPath();

                    if (
                        node.risk > 0.8
                    ) {
                        ctx.fillStyle =
                            "#ff3333";
                    }
                    else if (
                        node.risk > 0.4
                    ) {
                        ctx.fillStyle =
                            "#ffaa00";
                    }
                    else {
                        ctx.fillStyle =
                            "#00cc88";
                    }

                    ctx.arc(
                        node.x,
                        node.y,
                        7,
                        0,
                        2 * Math.PI
                    );

                    ctx.fill();

                    ctx.fillStyle =
                        "#ffffff";

                    ctx.fillText(
                        label,
                        node.x + 10,
                        node.y
                    );
                }}

            />

        </div>

    );
}
