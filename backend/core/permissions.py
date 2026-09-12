ROLE_PERMISSIONS = {

    "admin": [

        "cases:create",
        "cases:edit",
        "users:create",
        "system:manage"
    ],

    "analyst": [

        "cases:create",
        "cases:view",
        "graph:view",
        "copilot:use"
    ],

    "viewer": [

        "graph:view"
    ]
}
