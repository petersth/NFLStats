# NFL Statistics Application - Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Architecture](#system-architecture)
4. [Layer Descriptions](#layer-descriptions)
5. [Data Flow](#data-flow)
6. [Key Components](#key-components)
7. [Technology Stack](#technology-stack)
8. [Performance Strategies](#performance-strategies)
9. [Configuration System](#configuration-system)

## Overview

The NFL Statistics Application is an analytics platform that processes NFL play-by-play data to generate team performance metrics. The system provides statistical analysis, league rankings, and performance visualizations through a web interface.

### Key Features
- **NFL Data Processing**: Downloads and processes play-by-play data from the NFL API
- **Metrics Calculation**: Computes 14+ statistical metrics including success rate, yards per play, and red zone efficiency
- **League Rankings**: Calculates team rankings across all metrics with tie handling
- **Data Visualizations**: Provides charts, tables, and comparative analysis
- **Data Export**: Supports CSV, Excel, and JSON export formats
- **Configurable Analysis**: Allows filtering of QB kneels, spikes, and season types

## Architecture Principles

The application uses a layered architecture with the following principles:

### 1. **Separation of Concerns**
- Business logic is isolated in the Domain layer
- Infrastructure details are abstracted behind interfaces
- UI concerns are separated in the Presentation layer

### 2. **Dependency Inversion**
- High-level modules don't depend on low-level modules
- Both depend on abstractions (interfaces)
- Dependencies point inward toward the domain

### 3. **Single Responsibility**
- Each class/module has one reason to change
- Clear boundaries between layers
- Focused, cohesive components

### 4. **Testability**
- Business logic can be tested without UI or infrastructure
- Infrastructure can be mocked/stubbed
- Clear interfaces enable unit testing

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Streamlit Web UI                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Sidebar  │ │   Tabs   │ │  Charts  │ │  Export  │  │   │
│  │  │ Manager  │ │ Manager  │ │ Service  │ │ Service  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │Methodology│ │ Progress │ │ Metrics  │ │   App    │  │   │
│  │  │ Renderer │ │ Manager  │ │ Renderer │ │ Styling  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Use Case Controllers                  │   │
│  │  ┌────────────────────┐  ┌────────────────────────┐    │   │
│  │  │ TeamAnalysisRequest │  │ TeamAnalysisResponse   │    │   │
│  │  │      (DTO)          │  │        (DTO)           │    │   │
│  │  └────────────────────┘  └────────────────────────┘    │   │
│  │  ┌────────────────────┐  ┌────────────────────────┐    │   │
│  │  │ DataStatusInfo     │  │ SeasonContextInfo      │    │   │
│  │  │      (DTO)         │  │        (DTO)           │    │   │
│  │  └────────────────────┘  └────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Domain Layer                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     Core Business Logic                  │   │
│  │  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐  │   │
│  │  │   Entities   │ │  Calculators  │ │  Validators  │  │   │
│  │  │ (Team,Season,│ │(NFLStatsCalc) │ │(NFLValidator)│  │   │
│  │  │ GameStats)   │ │               │ │              │  │   │
│  │  └──────────────┘ └───────────────┘ └──────────────┘  │   │
│  │  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐  │   │
│  │  │   Metrics    │ │ Orchestration │ │ PlayFilter   │  │   │
│  │  │& Exceptions  │ │(Calc Orchestr)│ │& Services    │  │   │
│  │  └──────────────┘ └───────────────┘ └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    External Integrations                 │   │
│  │  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐  │   │
│  │  │ NFL Data API │ │ League Cache  │ │   Factories  │  │   │
│  │  │ Repository   │ │   (Memory)    │ │  (DI Setup)  │  │   │
│  │  └──────────────┘ └───────────────┘ └──────────────┘  │   │
│  │  ┌──────────────┐                   ┌──────────────┐  │   │
│  │  │  Streamlit   │                   │    Config    │  │   │
│  │  │  Framework   │                   │  Constants   │  │   │
│  │  │    Utils     │                   │              │  │   │
│  │  └──────────────┘                   └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Utilities Layer                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Cross-Cutting Concerns                    │   │
│  │  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐  │   │
│  │  │   Ranking    │ │ Configuration │ │    Season    │  │   │
│  │  │    Utils     │ │     Utils     │ │    Utils     │  │   │
│  │  └──────────────┘ └───────────────┘ └──────────────┘  │   │
│  │  ┌──────────────┐ ┌───────────────┐ ┌──────────────┐  │   │
│  │  │League Stats  │ │ Error Handling│ │ Config Hash/ │  │   │
│  │  │Utils/Metrics │ │   Decorators  │ │ NFL Metrics  │  │   │
│  │  └──────────────┘ └───────────────┘ └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. **Presentation Layer** (`src/presentation/`)
**Purpose**: User interface and interaction handling

**Components**:
- `StreamlitController`: Main application controller
- `SidebarManager`: Team/season selection and configuration
- `TabManager`: Multi-tab interface coordination
- `MetricsRenderer`: Statistical display formatting
- `ChartGenerationService`: Plotly chart creation
- `ExportService`: Data export functionality
- `MethodologyRenderer`: Calculation methodology explanations
- `ProgressManager`: Progress tracking and status updates
- `AppStyling`: UI styling and theme management

**Responsibilities**:
- Render UI components
- Handle user interactions
- Display visualizations
- Manage session state
- Export data in various formats
- Show calculation methodologies
- Track and display progress
- Apply consistent styling

### 2. **Application Layer** (`src/application/`)
**Purpose**: Coordinates use cases and data transformation

**Components**:
- `TeamAnalysisController`: Coordinates analysis workflow
- `TeamAnalysisRequest` (DTO): Input validation and structuring
- `TeamAnalysisResponse` (DTO): Output data packaging
- `DataStatusInfo` (DTO): Data freshness and status information
- `SeasonContextInfo` (DTO): Season context and validation messages
- `ExportFormat` (Enum): Supported export format definitions

**Responsibilities**:
- Validate input requests
- Coordinate domain services
- Transform data for presentation
- Handle use case flow
- Provide data status information
- Manage season context validation

### 3. **Domain Layer** (`src/domain/`)
**Purpose**: Core business logic and rules

**Components**:
- **Entities**: `Team`, `Season`, `Game`, `GameStats`, `SeasonStats`, `GameType`, `Location`
- **Services**: 
  - `NFLStatsCalculator`: Statistical calculations
  - `PlayFilter`: Play-by-play filtering logic
  - Domain services for data status and validation
- **Orchestration**:
  - `CalculationOrchestrator`: Coordinate calculations across services
- **Value Objects**: `PerformanceRank`, `TeamRecord`
- **Validators**: `NFLValidator` for business rule enforcement
- **Metrics & Exceptions**: `NFLMetrics` definitions and domain-specific exceptions

**Responsibilities**:
- Implement NFL statistical calculations
- Enforce business rules
- Define domain models
- Calculate success rates, rankings, averages
- Orchestrate complex calculations
- Handle domain-specific exceptions

### 4. **Infrastructure Layer** (`src/infrastructure/`)
**Purpose**: External system integration and technical concerns

**Components**:
- `UnifiedNFLRepository`: NFL API data access
- `LeagueStatsCache`: In-memory caching strategy
- `StreamlitUtils`: Framework integration utilities
- `Factories`: Dependency injection setup

**Sub-layers**:
- **Data**: NFL API integration and data access
- **Cache**: In-memory caching strategies
- **Frameworks**: Streamlit framework integrations

**Responsibilities**:
- Fetch data from NFL API (via nfl_data_py)
- Cache management
- Framework integration
- Technical infrastructure
- Dependency injection coordination

### 5. **Configuration Layer** (`src/config/`)
**Purpose**: Application configuration and constants

**Components**:
- `NFLConstants`: NFL-specific constants and team data
- Configuration definitions and default values

**Responsibilities**:
- Centralize NFL team data and metadata
- Define scoring constants and thresholds
- Provide configuration defaults

### 6. **Utilities Layer** (`src/utils/`)
**Purpose**: Cross-cutting concerns and helpers

**Components**:
- `ranking_utils`: League ranking calculations
- `configuration_utils`: Configuration management
- `season_utils`: Season filtering logic
- `error_handling`: Error decorators and handlers
- `league_stats_utils`: League-wide statistical utilities
- `nfl_metrics`: Metrics definitions and helpers
- `config_hasher`: Configuration hashing for caching

**Responsibilities**:
- League ranking calculations with tie handling
- Configuration management and validation
- Season filtering and date utilities
- Error handling and logging decorators
- Cross-cutting statistical utilities
- Configuration-based cache invalidation

## Data Flow

### 1. **User Interaction Flow**
```mermaid
User Input → Streamlit UI → Controller → Use Case → Domain → Infrastructure → NFL API
                ↑                                                              ↓
                └──────────── Response ←──────────────────────────────────────┘
```

### 2. **Data Processing Pipeline**
```text
1. User selects team, season, and configuration
2. Request validation in Application layer
3. Controller coordinates data fetching
4. Repository downloads NFL play-by-play data
5. PlayFilter applies configuration-based filtering
6. NFLStatsCalculator computes metrics:
   - Offensive efficiency (yards/play, success rate)
   - Passing metrics (completion %, yards)
   - Rushing metrics (yards/carry)
   - Scoring efficiency (points/drive, red zone TD%)
   - Situational metrics (3rd down %, turnovers)
7. RankingUtils calculates league-wide rankings
8. Response packaged with stats, rankings, and visualizations
9. UI renders results in tabs (Game Log, League Comparison, etc.)
```

### 3. **Caching Approach**
```text
First Request:  NFL API → Download → Cache → Process → Display
Subsequent:     Cache → Process → Display (skip download)
```

## Key Components

### NFLStatsCalculator
**Purpose**: Statistical calculations
**Location**: `src/domain/nfl_stats_calculator.py`

**Key Methods**:
- `calculate_season_stats()`: Aggregate season-level metrics
- `calculate_game_stats()`: Game-by-game breakdowns
- `_identify_successful_plays()`: Success rate calculation
- `_calculate_scoring_and_redzone_stats()`: Scoring efficiency

**Calculation Methods**:
- **Success Rate**: 
  - 1st down: ≥40% of yards to go
  - 2nd down: ≥60% of yards to go
  - 3rd/4th down: ≥100% of yards to go
- **Rankings**: Min-rank method with tie handling
- **Filtering**: Configuration-based exclusions (QB kneels, spikes)

### CalculationOrchestrator
**Purpose**: Coordinate complex calculations across multiple services
**Location**: `src/domain/orchestration/calculation_orchestrator.py`

**Key Features**:
- Coordinates NFLStatsCalculator and LeagueStatsCache
- Manages data flow between domain services
- Handles configuration-based calculation routing
- Provides unified interface for complex analysis workflows

### LeagueStatsCache
**Purpose**: Data caching for performance
**Location**: `src/infrastructure/cache/league_stats_cache.py`

**Approach**:
- In-memory cache for session persistence
- Hierarchical caching (complete season → filtered)
- Configuration-independent raw data caching
- Cache invalidation on new data requests
- Integration with NFLStatsCalculator for consistent results

### PlayFilter
**Purpose**: NFL-specific play filtering logic
**Location**: `src/domain/utilities/play_filter.py`

**Filters**:
- Offensive plays (rush + pass attempts)
- Exclude two-point conversions from regular plays
- Configuration-based exclusions (kneels, spikes)
- Context-aware filtering for different metrics

### MethodologyRenderer
**Purpose**: Display calculation methodologies and explanations
**Location**: `src/presentation/streamlit/components/methodology_renderer.py`

**Features**:
- Explains statistical calculation methods
- Shows success rate definitions
- Provides formula breakdowns
- Educational content for users

### ProgressManager
**Purpose**: Track and display progress during long-running operations
**Location**: `src/presentation/streamlit/components/progress_manager.py`

**Features**:
- Progress bar management
- Status message updates
- Milestone tracking
- User feedback during data processing

### StreamlitUtils
**Purpose**: Streamlit framework integration utilities
**Location**: `src/infrastructure/frameworks/streamlit_utils.py`

**Features**:
- Session state management
- Streamlit-specific UI helpers
- Framework abstraction layer
- Performance optimizations for Streamlit

## Technology Stack

### Core Technologies
- **Language**: Python 3.8+
- **Web Framework**: Streamlit 1.47.1
- **Data Processing**: Pandas 1.5.3, NumPy 1.26.4
- **Visualization**: Plotly 6.2.0
- **NFL Data**: nfl_data_py 0.3.3

### Key Libraries
```python
# requirements.txt (actual dependencies)
streamlit==1.47.1
pandas==1.5.3
numpy==1.26.4
nfl_data_py==0.3.3
plotly==6.2.0
openpyxl==3.1.2        # Excel export
requests==2.31.0       # HTTP requests
python-dateutil==2.8.2 # Date utilities
```

## Performance Strategies

### 1. **Caching**
- In-memory caching of NFL play-by-play data
- League-wide statistics cached per configuration
- Session-based cache persistence in Streamlit

### 2. **Lazy Loading**
- Tabs load content on-demand
- Charts generated only when viewed
- Progressive data loading with status updates

### 3. **Efficient Calculations**
- Vectorized operations with Pandas/NumPy
- Single-pass calculation for multiple metrics
- Pre-computed league statistics for rankings

### 4. **Data Optimization**
- Load only required columns from NFL API
- Filter data early in pipeline
- Reuse calculated intermediate results

## Configuration System

### User-Configurable Options
```python
{
    "include_qb_kneels_rushing": bool,      # Include QB kneels in rushing stats
    "include_qb_kneels_success_rate": bool, # Include in success rate
    "include_qb_spikes_completion": bool,   # Include spikes in completion %
    "include_qb_spikes_success_rate": bool  # Include in success rate
}
```

### Season Type Filters
- **ALL**: Regular season + playoffs
- **REG**: Regular season only
- **POST**: Playoffs only
