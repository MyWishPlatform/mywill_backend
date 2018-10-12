def create_eos_token_sa_json(token_address, bytecode, abi, admin_address, data):
    return {
        "actions": [
            {
                "account": "eosio",
                "name": "setabi",
                "authorization": [
                    {
                        "actor": token_address,
                        "permission": "active"
                    }
                ],
                "data": {
                    "account": token_address,
                    "abi": abi
                }
            },
            {
                "account": "eosio",
                "name": "setcode",
                "authorization": [
                    {
                        "actor": token_address,
                        "permission": "active"
                    }
                ],
                "data": {
                    "account": token_address,
                    "vmtype": 0,
                    "vmversion": 0,
                    "code": bytecode
                }
            },
            {
                "account": token_address,
                "name": "create",
                "authorization": [
                    {
                        "actor": token_address,
                        "permission": "active"
                    }
                ],
                "data": data
            },
            {
                "account": "eosio",
                "name": "updateauth",
                "authorization": [
                    {
                        "actor": token_address,
                        "permission": "owner"
                    }
                ],
                "data": {
                    "account": token_address,
                    "permission": "owner",
                    "parent": "",
                    "auth": {
                        "threshold": 1,
                        "keys": [],
                        "accounts": [
                            {
                                "permission": {
                                    "actor": admin_address,
                                    "permission": "owner"
                                },
                                "weight": 1
                            }
                        ],
                        "waits": []
                    }
                }
            },
            {
                "account": "eosio",
                "name": "updateauth",
                "authorization": [
                    {
                        "actor": token_address,
                        "permission": "active"
                    }
                ],
                "data": {
                    "account": token_address,
                    "permission": "active",
                    "parent": "owner",
                    "auth": {
                        "threshold": 1,
                        "keys": [],
                        "accounts": [
                            {
                                "permission": {
                                    "actor": admin_address,
                                    "permission": "eosio.code"
                                },
                                "weight": 1
                            }
                        ],
                        "waits": []
                    }
                }
            }
        ]
    }
