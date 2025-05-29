# MIT IDE Dashboard Data Pipeline

A comprehensive data pipeline for the MIT Initiative on the Digital Economy (IDE) Dashboard. This project automates the collection and processing of data from various sources including LinkedIn, YouTube, Medium, Google Scholar, and Eventbrite.

## Overview

The data pipeline is designed to:
- Collect data from multiple platforms
- Process and transform the data
- Store the data in Google Sheets
- Schedule regular updates
- Provide error handling and logging

## Features

- **Automated Data Collection**: Fetches data from multiple sources automatically
- **Scheduled Updates**: Runs updates quarterly (January, April, July, October)
- **Error Handling**: Robust error handling and logging system
- **Google Sheets Integration**: Stores all data in a centralized Google Sheet
- **Modular Design**: Easy to add new data sources or modify existing ones

## Prerequisites

- Python 3.8+
- Google Cloud Platform account with Sheets API enabled
- API keys for various services:
  - LinkedIn API
  - YouTube Data API
  - Eventbrite API
  - Google Scholar API

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/mit-ide-dashboard.git
cd mit-ide-dashboard
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```env
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
GOOGLE_SHEET_ID=your_sheet_id
EVENTBRITE_API_KEY=your_eventbrite_key
EVENTBRITE_PRIVATE_TOKEN=your_eventbrite_token
YOUTUBE_API_KEY=your_youtube_key
MIT_IDE_COMPANY_ID=your_linkedin_company_id
```

## Project Structure

```
mit-ide-dashboard/
├── data_pipeline/
│   ├── __init__.py
│   ├── data_updater.py
│   ├── linkedin_fetcher.py
│   ├── youtube_fetcher.py
│   ├── medium_fetcher.py
│   ├── scholar_fetcher.py
│   ├── eventbrite_fetcher.py
│   ├── budget_processor.py
│   └── sheets_manager.py
├── tests/
│   ├── __init__.py
│   ├── test_linkedin_fetcher.py
│   ├── test_youtube_fetcher.py
│   └── test_data_updater.py
├── requirements.txt
├── README.md
└── .env.example
```

## Usage

1. Run the data pipeline:
```bash
python -m data_pipeline.data_updater
```

2. The pipeline will:
   - Initialize all data fetchers
   - Run an initial data update
   - Schedule quarterly updates

## Data Sources

### LinkedIn
- Fetches company statistics for MIT IDE
- Updates follower counts and engagement metrics

### YouTube
- Collects video statistics
- Tracks views, comments, and subscriber counts

### Medium
- Gathers article statistics
- Monitors read times and engagement

### Google Scholar
- Tracks publication metrics
- Monitors citations and impact

### Eventbrite
- Collects event statistics
- Tracks attendance and engagement

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- MIT Initiative on the Digital Economy
- All contributors and maintainers

## Contact

For questions or support, please contact the MIT IDE team. 