import { useEffect, useState } from "react";

export default function CommunityExplorer() {

    const [rows, setRows] = useState([]);

    useEffect(() => {

        fetch(
            "http://localhost:8000/api/community/top"
        )
        .then(r => r.json())
        .then(setRows);

    }, []);

    return (
        <div>

            <h2>
                Communities
            </h2>

            {
                rows.map((row,index) => (

                    <div key={index}>

                        Community:
                        {row.community}

                        <br/>

                        Members:
                        {row.members}

                        <br/>

                        Avg Risk:
                        {
                            Number(
                                row.avg_risk
                            ).toFixed(4)
                        }

                        <hr/>

                    </div>

                ))
            }

        </div>
    );
}
