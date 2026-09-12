export default function SnapshotButton() {

    async function snapshot() {

        await fetch(
            "http://localhost:8000/api/snapshot",
            {
                method:"POST"
            }
        );
    }

    return (

        <button
            onClick={snapshot}
        >
            Save Graph Snapshot
        </button>

    );
}
