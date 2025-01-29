import json
import os
from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient
from fhir_proxy.proxy import adjust_urls
from httpx import Response


def test_adjust_urls():
    content = {
        "link": [
            {"url": "http://example.com/Patient?_id=123"},
            {"url": "http://example.com/Observation?_id=123"},
            {"url": "http://example.com/a/b/c/DocumentReference?_id=123"},
        ],
        "entry": [
            {"fullUrl": "http://example.com/Patient?_id=123"},
            {"fullUrl": "http://example.com/Observation?_id=123&foo=bar"},
            {"fullUrl": "http://example.com/a/b/c/DocumentReference?_id=123"},
            {"fullUrl": "http://example.com/a/b/c/DocumentReference/XXXXXXX"},
        ],
    }
    forwarded_host = "forwarded.example.com"
    forwarded_proto = "https"

    expected_content = {
        "link": [
            {"url": "https://forwarded.example.com/Patient?_id=123"},
            {"url": "https://forwarded.example.com/Observation?_id=123"},
            {"url": "https://forwarded.example.com/DocumentReference?_id=123"},
        ],
        "entry": [
            {"fullUrl": "https://forwarded.example.com/Patient?_id=123"},
            {"fullUrl": "https://forwarded.example.com/Observation?_id=123&foo=bar"},
            {"fullUrl": "https://forwarded.example.com/DocumentReference?_id=123"},
            {"fullUrl": "https://forwarded.example.com/DocumentReference/XXXXXXX"},
        ],
    }

    result = adjust_urls(content, forwarded_host, forwarded_proto)
    assert result == expected_content


@pytest.mark.asyncio
@respx.mock
@patch("fhir_proxy.proxy.fetch_token", return_value={"access_token": "mocked_token"})
async def test_vocabulary_patient(mock_fetch_token):
    from fhir_proxy.proxy import app

    assert os.getenv(
        "FHIR_SERVICE_URL"
    ), "FHIR_SERVICE_URL is not set. Please set env var to `http://example.com/fhir`"
    target_url = "http://example.com/fhir/Patient?_elements=extension,category,code,type"
    respx.get(target_url).mock(
        return_value=Response(200, json={
            "resourceType": "Bundle",
            "id": "53c922c2-a300-4dcf-bb64-51ad731851b0",
            "meta": {
                "lastUpdated": "2025-01-29T01:13:39.503+00:00"
            },
            "type": "searchset",
            "link": [{
                "relation": "self",
                "url": "https://hapi.test-fhir-aggregator.org/fhir/Patient?_elements=extension,category,code,type"
            }],
            "entry": [{
                "fullUrl": "https://hapi.test-fhir-aggregator.org/fhir/Patient/0368f85d-9028-5810-bda6-ec6ced4c0544",
                "resource": {
                    "resourceType": "Patient",
                    "id": "0368f85d-9028-5810-bda6-ec6ced4c0544",
                    "extension": [{
                        "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex",
                        "valueCode": "M"
                    }, {
                        "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                        "valueString": "white"
                    }, {
                        "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                        "valueString": "not hispanic or latino"
                    }, {
                        "url": "http://hl7.org/fhir/SearchParameter/patient-extensions-Patient-age",
                        "valueQuantity": {
                            "value": 63
                        }
                    }, {
                        "url": "http://example.org/fhir/StructureDefinition/part-of-study",
                        "valueReference": {
                            "reference": "ResearchStudy/ed0d94e6-51c3-5833-9a20-8ff1c5efc286"
                        }
                    }],
                    "gender": "male",
                },
                "search": {
                    "mode": "match"
                }
            },
                {
                    "fullUrl": "https://hapi.test-fhir-aggregator.org/fhir/Patient/bd185005-11c2-55e7-a148-506d57abfce6",
                    "resource": {
                        "resourceType": "Patient",
                        "id": "bd185005-11c2-55e7-a148-506d57abfce6",
                        "meta": {
                            "versionId": "1",
                            "lastUpdated": "2025-01-23T00:18:41.574+00:00"
                        },
                        "extension": [{
                            "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex",
                            "valueCode": "F"
                        }, {
                            "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                            "valueString": "white"
                        }, {
                            "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                            "valueString": "not reported"
                        }, {
                            "url": "http://hl7.org/fhir/SearchParameter/patient-extensions-Patient-age",
                            "valueQuantity": {
                                "value": 55
                            }
                        }, {
                            "url": "http://example.org/fhir/StructureDefinition/part-of-study",
                            "valueReference": {
                                "reference": "ResearchStudy/ed0d94e6-51c3-5833-9a20-8ff1c5efc286"
                            }
                        }],
                        "gender": "female"
                    },
                    "search": {
                        "mode": "match"
                    }
                }
            ]
        })
    )

    expected_result = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "code",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": []
                }
            },
            {
                "name": "category",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": []
                }
            },
            {
                "name": "extension",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [
                        {
                            "name": "M",
                            "valueInteger": 1
                        },
                        {
                            "name": "white",
                            "valueInteger": 2
                        },
                        {
                            "name": "not hispanic or latino",
                            "valueInteger": 1
                        },
                        {
                            "name": "63",
                            "valueInteger": 1
                        },
                        {
                            "name": "ResearchStudy/ed0d94e6-51c3-5833-9a20-8ff1c5efc286",
                            "valueInteger": 2
                        },
                        {
                            "name": "F",
                            "valueInteger": 1
                        },
                        {
                            "name": "not reported",
                            "valueInteger": 1
                        },
                        {
                            "name": "55",
                            "valueInteger": 1
                        }
                    ]
                }
            }
        ]
    }

    # Make a request to the proxy
    client = TestClient(app)
    response = client.get(
        "/Patient/$vocabulary",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 200
    actual_result = response.json()
    print(json.dumps(actual_result, indent=2))
    assert actual_result == expected_result


@pytest.mark.asyncio
@respx.mock
@patch("fhir_proxy.proxy.fetch_token", return_value={"access_token": "mocked_token"})
async def test_vocabulary_observation(mock_fetch_token):
    from fhir_proxy.proxy import app

    assert os.getenv(
        "FHIR_SERVICE_URL"
    ), "FHIR_SERVICE_URL is not set. Please set env var to `http://example.com/fhir`"
    target_url = "http://example.com/fhir/Observation?_elements=extension,category,code,type"
    respx.get(target_url).mock(
        return_value=Response(
            status_code=200,
            json={
                "entry": [
                    {
                        "fullUrl": "https://google-fhir.fhir-aggregator.org/Condition/8003bd68-c75d-52b0-8856-ed17f406835f",
                        "resource": {
                            "bodySite": [
                                {
                                    "coding": [
                                        {
                                            "code": "110736001",
                                            "display": "Bronchus and lung",
                                            "system": "http://snomed.info/sct"
                                        }
                                    ]
                                }
                            ],
                            "category": [
                                {
                                    "coding": [
                                        {
                                            "code": "encounter-diagnosis",
                                            "display": "Encounter Diagnosis",
                                            "system": "http://terminology.hl7.org/CodeSystem/condition-category"
                                        },
                                        {
                                            "code": "439401001",
                                            "display": "Diagnosis",
                                            "system": "http://snomed.info/sct"
                                        }
                                    ]
                                }
                            ],
                            "clinicalStatus": {
                                "coding": [
                                    {
                                        "code": "unknown",
                                        "display": "unknown",
                                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"
                                    }
                                ]
                            },
                            "code": {
                                "coding": [
                                    {
                                        "code": "Squamous cell carcinoma, NOS",
                                        "display": "Squamous cell carcinoma, NOS",
                                        "system": "https://gdc.cancer.gov/primary_diagnosis"
                                    }
                                ]
                            },
                            "encounter": {
                                "reference": "Encounter/ae0ed86b-7945-5de0-ab41-4b26ab2f84a1"
                            },
                            "extension": [
                                {
                                    "url": "http://example.org/fhir/StructureDefinition/part-of-study",
                                    "valueReference": {
                                        "reference": "ResearchStudy/687eece2-87f6-5ebd-94db-e97497b57498"
                                    }
                                }
                            ],
                            "id": "8003bd68-c75d-52b0-8856-ed17f406835f",
                            "identifier": [
                                {
                                    "system": "https://gdc.cancer.gov/submitter_diagnosis_id",
                                    "use": "official",
                                    "value": "TCGA-37-3789_diagnosis"
                                }
                            ],
                            "meta": {
                                "lastUpdated": "2025-01-28T01:05:18.283307+00:00"
                            },
                            "onsetAge": {
                                "code": "d",
                                "system": "http://unitsofmeasure.org",
                                "unit": "days",
                                "value": 23782
                            },
                            "resourceType": "Condition",
                            "stage": [
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/a23b319b-9adf-5b86-b1f2-e63bb4050bd1"
                                        },
                                        {
                                            "reference": "Observation/d69bf598-3e71-5648-a998-4dd283e0eeff"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C48705",
                                                "display": "N0",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3203106",
                                                "display": "N0",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222590007",
                                                "display": "N0",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/f2eaa600-5584-59d3-a2e9-b1d93e08f5f6"
                                        },
                                        {
                                            "reference": "Observation/d69bf598-3e71-5648-a998-4dd283e0eeff"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C27976",
                                                "display": "Stage IB",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3203222",
                                                "display": "Stage IB",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222593009",
                                                "display": "Stage IB",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/57730708-cf4b-5ab3-b773-3c1a5eb7c83f"
                                        },
                                        {
                                            "reference": "Observation/d69bf598-3e71-5648-a998-4dd283e0eeff"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C48724",
                                                "display": "T2",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3045435",
                                                "display": "T2",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222589003",
                                                "display": "T2",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/d69bf598-3e71-5648-a998-4dd283e0eeff"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "2785839",
                                                "display": "Not Reported",
                                                "system": "https://cadsr.cancer.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "2785839",
                                                "display": "neoplasm_histologic_grade",
                                                "system": "https://cadsr.cancer.gov"
                                            }
                                        ]
                                    }
                                }
                            ],
                            "subject": {
                                "reference": "Patient/d93548fb-8c38-5223-9927-ef38b3ee76f1"
                            }
                        },
                        "search": {
                            "mode": "match"
                        }
                    },
                    {
                        "fullUrl": "https://google-fhir.fhir-aggregator.org/Condition/24eb37d8-2e4a-536a-9a67-31675e54db53",
                        "resource": {
                            "bodySite": [
                                {
                                    "coding": [
                                        {
                                            "code": "110736001",
                                            "display": "Bronchus and lung",
                                            "system": "http://snomed.info/sct"
                                        }
                                    ]
                                }
                            ],
                            "category": [
                                {
                                    "coding": [
                                        {
                                            "code": "encounter-diagnosis",
                                            "display": "Encounter Diagnosis",
                                            "system": "http://terminology.hl7.org/CodeSystem/condition-category"
                                        },
                                        {
                                            "code": "439401001",
                                            "display": "Diagnosis",
                                            "system": "http://snomed.info/sct"
                                        }
                                    ]
                                }
                            ],
                            "clinicalStatus": {
                                "coding": [
                                    {
                                        "code": "unknown",
                                        "display": "unknown",
                                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"
                                    }
                                ]
                            },
                            "code": {
                                "coding": [
                                    {
                                        "code": "Basaloid squamous cell carcinoma",
                                        "display": "Basaloid squamous cell carcinoma",
                                        "system": "https://gdc.cancer.gov/primary_diagnosis"
                                    }
                                ]
                            },
                            "encounter": {
                                "reference": "Encounter/2102b2f4-10fb-5ff0-aa91-bfc53ae8e2b7"
                            },
                            "extension": [
                                {
                                    "url": "http://example.org/fhir/StructureDefinition/part-of-study",
                                    "valueReference": {
                                        "reference": "ResearchStudy/687eece2-87f6-5ebd-94db-e97497b57498"
                                    }
                                }
                            ],
                            "id": "24eb37d8-2e4a-536a-9a67-31675e54db53",
                            "identifier": [
                                {
                                    "system": "https://gdc.cancer.gov/submitter_diagnosis_id",
                                    "use": "official",
                                    "value": "TCGA-58-A46N_diagnosis"
                                }
                            ],
                            "meta": {
                                "lastUpdated": "2025-01-28T01:05:18.281939+00:00"
                            },
                            "onsetAge": {
                                "code": "d",
                                "system": "http://unitsofmeasure.org",
                                "unit": "days",
                                "value": 19050
                            },
                            "resourceType": "Condition",
                            "stage": [
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/6e96d655-9754-526d-9d68-7f14a8186899"
                                        },
                                        {
                                            "reference": "Observation/28d02378-18de-5659-8d6c-482955c6250b"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C48699",
                                                "display": "M0",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3045439",
                                                "display": "M0",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222587001",
                                                "display": "M0",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/bdf967ae-65a9-55c6-9262-6fe2f890b8f2"
                                        },
                                        {
                                            "reference": "Observation/28d02378-18de-5659-8d6c-482955c6250b"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C48705",
                                                "display": "N0",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3203106",
                                                "display": "N0",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222590007",
                                                "display": "N0",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/2f4e12c0-34cb-5991-bd86-ced3fa2c5cbf"
                                        },
                                        {
                                            "reference": "Observation/28d02378-18de-5659-8d6c-482955c6250b"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C27976",
                                                "display": "Stage IB",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3203222",
                                                "display": "Stage IB",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222593009",
                                                "display": "Stage IB",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/4fb2da9c-1202-54ea-ab39-11fad590fa47"
                                        },
                                        {
                                            "reference": "Observation/28d02378-18de-5659-8d6c-482955c6250b"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "C48725",
                                                "display": "T2a",
                                                "system": "https://ncit.nci.nih.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "3045435",
                                                "display": "T2a",
                                                "system": "https://cadsr.cancer.gov/"
                                            },
                                            {
                                                "code": "1222589003",
                                                "display": "T2a",
                                                "system": "http://snomed.info/sct"
                                            }
                                        ]
                                    }
                                },
                                {
                                    "assessment": [
                                        {
                                            "reference": "Observation/28d02378-18de-5659-8d6c-482955c6250b"
                                        }
                                    ],
                                    "summary": {
                                        "coding": [
                                            {
                                                "code": "2785839",
                                                "display": "Not Reported",
                                                "system": "https://cadsr.cancer.gov"
                                            }
                                        ]
                                    },
                                    "type": {
                                        "coding": [
                                            {
                                                "code": "2785839",
                                                "display": "neoplasm_histologic_grade",
                                                "system": "https://cadsr.cancer.gov"
                                            }
                                        ]
                                    }
                                }
                            ],
                            "subject": {
                                "reference": "Patient/f0a00da8-94a0-52c9-aacc-2998308aa6bb"
                            }
                        },
                        "search": {
                            "mode": "match"
                        }
                    }
                ],
                "link": [
                    {
                        "relation": "self",
                        "url": "https://google-fhir.fhir-aggregator.org/Condition?_count=2"
                    }
                ],
                "resourceType": "Bundle",
                "total": 3188,
                "type": "searchset"
            }
        )
    )

    expected_result = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "code",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [
                        {
                            "name": "Squamous cell carcinoma, NOS",
                            "valueInteger": 1
                        },
                        {
                            "name": "Basaloid squamous cell carcinoma",
                            "valueInteger": 1
                        }
                    ]
                }
            },
            {
                "name": "category",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [
                        {
                            "name": "Encounter Diagnosis",
                            "valueInteger": 2
                        },
                        {
                            "name": "Diagnosis",
                            "valueInteger": 2
                        }
                    ]
                }
            },
            {
                "name": "extension",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [
                        {
                            "name": "ResearchStudy/687eece2-87f6-5ebd-94db-e97497b57498",
                            "valueInteger": 2
                        }
                    ]
                }
            }
        ]
    }

    # Make a request to the proxy
    client = TestClient(app)
    response = client.get(
        "/Observation/$vocabulary",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 200
    actual_result = response.json()
    print(json.dumps(actual_result, indent=2))
    assert actual_result == expected_result


@pytest.mark.asyncio
@respx.mock
@patch("fhir_proxy.proxy.fetch_token", return_value={"access_token": "mocked_token"})
async def test_fhir_proxy_get(mock_fetch_token):
    # Mock the target FHIR service URL
    from fhir_proxy.proxy import app

    assert os.getenv(
        "FHIR_SERVICE_URL"
    ), "FHIR_SERVICE_URL is not set. Please set env var to `http://example.com/fhir`"
    target_url = "http://example.com/fhir/Patient?_id=123"
    respx.get(target_url).mock(
        return_value=Response(200, json={"resourceType": "Bundle"})
    )

    target_url = "http://example.com/fhir/does-not-exist.txt"
    respx.get(target_url).mock(return_value=Response(404))

    # create a mock for the fetch_token function

    # Make a request to the proxy
    client = TestClient(app)
    response = client.get(
        "/Patient?_id=123",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"resourceType": "Bundle"}

    response = client.get(
        "/does-not-exist.txt",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 404
