import { useEffect, useState } from "react";

export default function CaseManagement() {

    const [cases,setCases] =
        useState([]);

    const [title,setTitle] =
        useState("");

    const [description,setDescription] =
        useState("");

    async function loadCases() {

        const response =
        await fetch(
            "http://localhost:8000/api/cases"
        );

        const data =
        await response.json();

        setCases(data);
    }

    async function createCase() {

        await fetch(
            "http://localhost:8000/api/cases",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({
                    title,
                    description
                })
            }
        );

        loadCases();
    }

    useEffect(() => {
        loadCases();
    }, []);

    return (

        <div>

            <h2>
                Investigation Cases
            </h2>

            <input
                value={title}
                onChange={(e)=>
                    setTitle(
                        e.target.value
                    )
                }
                placeholder="Title"
            />

            <input
                value={description}
                onChange={(e)=>
                    setDescription(
                        e.target.value
                    )
                }
                placeholder="Description"
            />

            <button
                onClick={createCase}
            >
                Create
            </button>

            <hr/>

            {
                cases.map(
                    (c,index)=>(
                    <div key={index}>

                        <h4>
                            {c.title}
                        </h4>

                        <p>
                            {c.status}
                        </p>

                        <p>
                            {c.description}
                        </p>

                        <hr/>

                    </div>
                ))
            }

        </div>
    );
}
