from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
from scholarly import scholarly
from collections import defaultdict

# Load environment variables
load_dotenv()

app = FastAPI(
    title="MIT IDE Dashboard API",
    description="Dashboard for MIT Initiative on the Digital Economy",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class Event(BaseModel):
    id: str
    name: str
    date: str
    attendees: int
    capacity: int
    description: Optional[str] = None

class Publication(BaseModel):
    title: str
    authors: List[str]
    year: int
    citations: int
    venue: str
    researcher: str  # Added to track which IDE researcher it belongs to

class ResearcherStats(BaseModel):
    name: str
    scholar_id: str
    role: str
    total_citations: int
    h_index: int
    i10_index: int
    publications: List[Publication]

class PublicationResponse(BaseModel):
    researchers: List[ResearcherStats]
    aggregated_stats: Dict[str, Any]

class LinkedInMetrics(BaseModel):
    date: str
    impressions: int
    engagements: int
    followers: int

class Budget(BaseModel):
    year: int
    total: float
    categories: Dict[str, float]

class ResearcherTable(BaseModel):
    name: str
    publications: int
    citations: int

# Mock Data
MOCK_EVENTS = [
    Event(
        id="1",
        name="Digital Economy Summit 2024",
        date="2024-03-15T09:00:00Z",
        attendees=150,
        capacity=200,
        description="Annual summit on digital economy trends"
    ),
    Event(
        id="2",
        name="AI in Business Workshop",
        date="2024-04-20T10:00:00Z",
        attendees=75,
        capacity=100,
        description="Hands-on workshop on AI applications"
    )
]

MOCK_PUBLICATIONS = [
    Publication(
        title="The Impact of Digital Transformation on Business Models",
        authors=["John Doe", "Jane Smith"],
        year=2023,
        citations=45,
        venue="Harvard Business Review",
        researcher="John Doe"
    ),
    Publication(
        title="Machine Learning Applications in Financial Services",
        authors=["Jane Smith", "Mike Johnson"],
        year=2022,
        citations=32,
        venue="Sloan Management Review",
        researcher="Jane Smith"
    )
]

MOCK_LINKEDIN_METRICS = [
    LinkedInMetrics(
        date="2024-03-01",
        impressions=1500,
        engagements=120,
        followers=5000
    ),
    LinkedInMetrics(
        date="2024-03-15",
        impressions=2000,
        engagements=180,
        followers=5200
    )
]

MOCK_BUDGET = [
    Budget(
        year=2023,
        total=1000000,
        categories={
            "research": 400000,
            "events": 200000,
            "operations": 150000,
            "personnel": 200000,
            "outreach": 30000,
            "other": 20000
        }
    ),
    Budget(
        year=2024,
        total=1200000,
        categories={
            "research": 500000,
            "events": 250000,
            "operations": 180000,
            "personnel": 220000,
            "outreach": 40000,
            "other": 10000
        }
    )
]

# Google Scholar IDs for MIT IDE researchers with names and roles
SCHOLARS = [
    # Research Group Leads
    {"id": "E2uuNVoAAAAJ", "name": "Sinan Aral", "role": "Research Group Lead"},
    {"id": "oNQRPLYAAAAJ", "name": "Dean Eckles", "role": "Research Group Lead"},
    {"id": "L_O2kH0AAAAJ", "name": "John Horton", "role": "Research Group Lead"},
    {"id": "YArJECsAAAAJ", "name": "Andrew McAfee", "role": "Research Group Lead"},
    {"id": "P4nfoKYAAAAJ", "name": "Alex 'Sandy' Pentland", "role": "Research Group Lead"},
    {"id": "C0ANojIAAAAJ", "name": "David Rand", "role": "Research Group Lead"},
    {"id": "yjttFw4AAAAJ", "name": "Neil Thompson", "role": "Research Group Lead"},
    
    # Research Scientists
    {"id": "l9Or8EMAAAAJ", "name": "Daron Acemoglu", "role": "Research Scientist"},
    {"id": "nzUHgC0AAAAJ", "name": "Martin Fleming", "role": "Research Scientist"},
    {"id": "594kFtAAAAAJ", "name": "Hans Gundlach", "role": "Research Scientist"},
    {"id": "oyDFgiIAAAAJ", "name": "Brittany Harris", "role": "Research Scientist"},
    {"id": "vGN58VQAAAAJ", "name": "Jayson Lynch", "role": "Research Scientist"},
    {"id": "mIlSY3IAAAAJ", "name": "Kristina McElheran", "role": "Research Scientist"},
    {"id": "He__Th0AAAAJ", "name": "Geoffrey Parker", "role": "Research Scientist"},
    {"id": "pXNKpl8AAAAJ", "name": "Ana Trisovic", "role": "Research Scientist"},
    
    # Digital Fellows
    {"id": "8T7L96IAAAAJ", "name": "Elizabeth Altman", "role": "Digital Fellow"},
    {"id": "4VRi-bMAAAAJ", "name": "Matt Beane", "role": "Digital Fellow"},
    {"id": "LGTNl2gAAAAJ", "name": "Seth Benzell", "role": "Digital Fellow"},
    {"id": "uHkRlUoAAAAJ", "name": "Sukwoong Choi", "role": "Digital Fellow"},
    {"id": "QUhNN6QAAAAJ", "name": "Thomas Davenport", "role": "Digital Fellow"},
    {"id": "vu5Mw_0AAAAJ", "name": "Paramveer Dhillon", "role": "Digital Fellow"},
    {"id": "0BebkaYAAAAJ", "name": "Apostolos Filippas", "role": "Digital Fellow"}
]

async def get_google_scholar_publications() -> PublicationResponse:
    researchers = []
    total_publications = 0
    total_citations = 0
    citations_by_role = defaultdict(int)
    publications_by_role = defaultdict(int)
    
    for scholar in SCHOLARS:
        try:
            author = scholarly.search_author_id(scholar["id"])
            if not author:
                continue
                
            author = scholarly.fill(author)
            if not author:
                continue

            publications = []
            if 'publications' in author:
                for pub in list(author['publications'])[:10]:  # Get 10 most recent publications
                    try:
                        pub = scholarly.fill(pub)
                        if pub and 'bib' in pub:
                            publications.append(Publication(
                                title=pub['bib'].get('title', ''),
                                authors=pub['bib'].get('author', '').split(' and ') if pub['bib'].get('author') else [],
                                year=int(pub['bib'].get('pub_year', 0)),
                                citations=pub.get('num_citations', 0),
                                venue=pub['bib'].get('venue', ''),
                                researcher=scholar["name"]
                            ))
                    except Exception as e:
                        print(f"Error processing publication: {str(e)}")
                        continue

            researcher_stats = ResearcherStats(
                name=scholar["name"],
                scholar_id=scholar["id"],
                role=scholar["role"],
                total_citations=author.get('citedby', 0),
                h_index=author.get('hindex', 0),
                i10_index=author.get('i10index', 0),
                publications=publications
            )
            
            researchers.append(researcher_stats)
            total_publications += len(publications)
            total_citations += author.get('citedby', 0)
            citations_by_role[scholar["role"]] += author.get('citedby', 0)
            publications_by_role[scholar["role"]] += len(publications)
            
        except Exception as e:
            print(f"Error fetching publications for scholar {scholar['id']}: {str(e)}")
            continue
    
    # Calculate aggregated statistics
    aggregated_stats = {
        "total_researchers": len(researchers),
        "total_publications": total_publications,
        "total_citations": total_citations,
        "average_citations_per_researcher": total_citations // len(researchers) if researchers else 0,
        "citations_by_role": dict(citations_by_role),
        "publications_by_role": dict(publications_by_role),
        "researchers_by_role": {
            "Research Group Lead": len([r for r in researchers if r.role == "Research Group Lead"]),
            "Research Scientist": len([r for r in researchers if r.role == "Research Scientist"]),
            "Digital Fellow": len([r for r in researchers if r.role == "Digital Fellow"])
        }
    }
    
    # Sort researchers by total citations
    researchers.sort(key=lambda x: x.total_citations, reverse=True)
    
    return PublicationResponse(
        researchers=researchers,
        aggregated_stats=aggregated_stats
    )

# Dashboard HTML
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MIT IDE Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .card {
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto px-4 py-8">
        <header class="text-center mb-12">
            <h1 class="text-4xl font-bold text-gray-800">MIT IDE Dashboard</h1>
            <p class="text-xl text-gray-600">Initiative on the Digital Economy</p>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="card bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Events</h2>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Upcoming Events</span>
                        <span class="font-bold">2</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Total Capacity</span>
                        <span class="font-bold">300</span>
                    </div>
                </div>
            </div>

            <div class="card bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Publications</h2>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Total Publications</span>
                        <span class="font-bold">2</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Total Citations</span>
                        <span class="font-bold">77</span>
                    </div>
                </div>
            </div>

            <div class="card bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-xl font-semibold mb-4">LinkedIn</h2>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Followers</span>
                        <span class="font-bold">5,200</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Engagement Rate</span>
                        <span class="font-bold">9%</span>
                    </div>
                </div>
            </div>

            <div class="card bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Budget</h2>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">2024 Budget</span>
                        <span class="font-bold">$1.2M</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-600">Growth</span>
                        <span class="font-bold text-green-600">+20%</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div class="card bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Upcoming Events</h2>
                <div class="space-y-4">
                    <div class="border-b pb-4">
                        <h3 class="font-semibold">Digital Economy Summit 2024</h3>
                        <p class="text-gray-600">March 15, 2024</p>
                        <div class="mt-2">
                            <div class="w-full bg-gray-200 rounded-full h-2.5">
                                <div class="bg-blue-600 h-2.5 rounded-full" style="width: 75%"></div>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">150/200 attendees</p>
                        </div>
                    </div>
                    <div>
                        <h3 class="font-semibold">AI in Business Workshop</h3>
                        <p class="text-gray-600">April 20, 2024</p>
                        <div class="mt-2">
                            <div class="w-full bg-gray-200 rounded-full h-2.5">
                                <div class="bg-blue-600 h-2.5 rounded-full" style="width: 75%"></div>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">75/100 attendees</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card bg-white rounded-lg shadow-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Recent Publications</h2>
                <div class="space-y-4">
                    <div class="border-b pb-4">
                        <h3 class="font-semibold">The Impact of Digital Transformation on Business Models</h3>
                        <p class="text-gray-600">MIT Sloan Management Review, 2023</p>
                        <p class="text-sm text-blue-600 mt-1">45 citations</p>
                    </div>
                    <div>
                        <h3 class="font-semibold">Machine Learning in Financial Markets</h3>
                        <p class="text-gray-600">Journal of Financial Economics, 2024</p>
                        <p class="text-sm text-blue-600 mt-1">32 citations</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // You can add interactive charts here using Chart.js
        document.addEventListener('DOMContentLoaded', function() {
            // Example chart initialization
            const ctx = document.createElement('canvas');
            document.querySelector('.container').appendChild(ctx);
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Research', 'Events', 'Operations', 'Personnel', 'Outreach', 'Other'],
                    datasets: [{
                        label: '2024 Budget Distribution',
                        data: [500000, 250000, 180000, 220000, 40000, 10000],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.5)',
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 206, 86, 0.5)',
                            'rgba(75, 192, 192, 0.5)',
                            'rgba(153, 102, 255, 0.5)',
                            'rgba(255, 159, 64, 0.5)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Budget Distribution'
                        }
                    }
                }
            });
        });
    </script>
</body>
</html>
"""

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML

@app.get("/events", response_model=List[Event])
async def get_events():
    return MOCK_EVENTS

@app.get("/publications", response_model=PublicationResponse)
async def get_publications():
    try:
        return await get_google_scholar_publications()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/linkedin", response_model=List[LinkedInMetrics])
async def get_linkedin_metrics():
    return MOCK_LINKEDIN_METRICS

@app.get("/budget", response_model=List[Budget])
async def get_budget():
    return MOCK_BUDGET

@app.get("/researchers", response_model=List[ResearcherTable])
async def get_researchers_table():
    try:
        # Get the full publication data
        pub_data = await get_google_scholar_publications()
        
        # Transform into table format
        researchers = []
        for researcher in pub_data.researchers:
            researchers.append(ResearcherTable(
                name=researcher.name,
                publications=len(researcher.publications),
                citations=researcher.total_citations
            ))
        
        # Sort by citations (descending)
        researchers.sort(key=lambda x: x.citations, reverse=True)
        
        return researchers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 