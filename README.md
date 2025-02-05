# Casca Engineering Intern Coding Challenge
# Frontend
A React-based web application for analyzing bank statements serving as an MVP for the Casca Engineering Intern coding challenge. Features real-time transaction categorization, interactive visualizations, and anomaly detection. The interface is styled using Tailwind CSS, incorporating shadcn/ui components.

## Features
### Core Functionality

- PDF Bank Statement Upload
- Automated Transaction Analysis
- Real-time Data Processing
- Currency Support (USD, EUR, GBP, JPY)
- Interactive Transaction Management

### Data Visualization

- Transaction History Line Chart
- Category Distribution Pie Chart
- Comprehensive Financial Summary
- Unusual Activity Detection

### Transaction Management

- Interactive Transaction Table
- Category-based Filtering
- Transaction Review Modal
- ML-model Training Integration

## UI Components
The application utilizes the following major components:

### Dashboard Elements

- Summary Cards (Income, Expenses, Net Change)
- Transaction History Graph
- Category Distribution Chart
- Tabbed Interface for Different Views

### Interactive Features

- File Upload Interface
- Transaction Review Modal
- Category Selection
- Data Update System

## Technical Implementation

### Key Components

### BankStatementApp (Main Component)

```
interface Transaction {
  check_no: string;
  date: string;
  description: string;
  amount: string;
  category: string;
  image_file?: string;
  is_unusual?: boolean;
}

interface StatementData {
  summary: {
    total_income: number;
    total_expenses: number;
    net_change: number;
    largest_expense: { amount: number, description: string, date: string };
    largest_income: { amount: number, description: string, date: string };
  };
  all_transactions: Transaction[];
  currency: string;
  category_breakdown: { [key: string]: number };
  statement_info: {
    opening_balance: number;
    closing_balance: number;
  };
  unusual_transactions: Transaction[];
}
```

### Data Visualization

- Uses Recharts for responsive charts
- Implements both line and pie charts
- Custom formatting for currency display

### Transaction Management

- Interactive data tables
- Modal-based transaction editing
- Category management system

## State Management

The application manages several key states:

```
const [data, setData] = useState<StatementData | null>(null);
const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
const [showReviewModal, setShowReviewModal] = useState(false);
const [isLoading, setIsLoading] = useState(false);
const [trainMessage, setTrainMessage] = useState<string | null>(null);
```

## API Integration
The application connects to a backend service with the following endpoints:

- ```/process-statement``` - PDF processing and initial analysis
- ```/update-transaction``` - Transaction updates and model training

## Features in Detail

### Statement Processing

- Supports PDF file upload
- Automated data extraction
- Real-time processing status updates
- For statements with check-images (currently only US Bank for now), extracts individual checks and displays them in a modal view for users to provide granular detail changes to description, categorization, or amount. 

### Data Analysis

- Transaction categorization
- Anomaly detection
- Spending pattern analysis
- Historical trend visualization

## Setup and Installation
### Prerequisites

- Node.js (v16.8 or higher)
- npm or yarn

### Installation Steps

```
# Clone repository
git clone https://github.com/LaUrrego/casca-project.git

# Move into frontend
cd frontend
```

-  Install base dependencies:
```
npm install
```

- Setup Tailwind CSS for Vite, official documentation [here](https://tailwindcss.com/docs/installation/using-vite) `note: There are current known uses installing shadecn/ui and Tailwind 4. Recommend using @3.4.17 for now.`:

```
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss@3.4.17 init --full
```

- Configure your `tailwind.config.js`:
```
/** @type {import('tailwindcss').Config} */
export default {
	darkMode: ["class"],
	content: [
	  './pages/**/*.{ts,tsx}',
	  './components/**/*.{ts,tsx}',
	  './app/**/*.{ts,tsx}',
	  './src/**/*.{ts,tsx}',
	],
	prefix: "",
	theme: {
	  container: {
		center: true,
		padding: "2rem",
		screens: {
		  "2xl": "1400px",
		},
	  },
	  extend: {
		colors: {
		  border: "hsl(var(--border))",
		  input: "hsl(var(--input))",
		  ring: "hsl(var(--ring))",
		  background: "hsl(var(--background))",
		  foreground: "hsl(var(--foreground))",
		  primary: {
			DEFAULT: "hsl(var(--primary))",
			foreground: "hsl(var(--primary-foreground))",
		  },
		  secondary: {
			DEFAULT: "hsl(var(--secondary))",
			foreground: "hsl(var(--secondary-foreground))",
		  },
		  destructive: {
			DEFAULT: "hsl(var(--destructive))",
			foreground: "hsl(var(--destructive-foreground))",
		  },
		  muted: {
			DEFAULT: "hsl(var(--muted))",
			foreground: "hsl(var(--muted-foreground))",
		  },
		  accent: {
			DEFAULT: "hsl(var(--accent))",
			foreground: "hsl(var(--accent-foreground))",
		  },
		  popover: {
			DEFAULT: "hsl(var(--popover))",
			foreground: "hsl(var(--popover-foreground))",
		  },
		  card: {
			DEFAULT: "hsl(var(--card))",
			foreground: "hsl(var(--card-foreground))",
		  },
		},
		borderRadius: {
		  lg: "var(--radius)",
		  md: "calc(var(--radius) - 2px)",
		  sm: "calc(var(--radius) - 4px)",
		},
		keyframes: {
		  "accordion-down": {
			from: { height: "0" },
			to: { height: "var(--radix-accordion-content-height)" },
		  },
		  "accordion-up": {
			from: { height: "var(--radix-accordion-content-height)" },
			to: { height: "0" },
		  },
		  "overlay-show": {
			from: { opacity: "0" },
			to: { opacity: "1" },
		  },
		  "content-show": {
			from: { opacity: "0", transform: "translate(-50%, -48%) scale(0.96)" },
			to: { opacity: "1", transform: "translate(-50%, -50%) scale(1)" },
		  },
		},
		animation: {
		  "accordion-down": "accordion-down 0.2s ease-out",
		  "accordion-up": "accordion-up 0.2s ease-out",
		  "overlay-show": "overlay-show 150ms cubic-bezier(0.16, 1, 0.3, 1)",
		  "content-show": "content-show 150ms cubic-bezier(0.16, 1, 0.3, 1)",
		},
	  },
	},
	plugins: ["tailwindcss-animate"],
  }
```

- Add the Tailwind directives to `src/index.css`:
```
@tailwind base;
@tailwind components;
@tailwind utilities;
```
- Install additional required dependencies for `shadcn/ui`:
```
npm install @radix-ui/react-dialog @radix-ui/react-tabs @radix-ui/react-select lucide-react tailwindcss-animate class-variance-authority clsx tailwind-merge
```
- Configure your `tsconfig.json` to include the following paths:
```
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}

```
- Configure `tsconfig.app.json`:
```
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": {
      "@/*": [
        "./src/*"
      ]
    },

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}

```

- Update path in `vite.config.ts`:
```
npm install -D @types/node

```

```
import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

- Install `shadecn/ui`, official documentation [here](https://ui.shadcn.com/docs/installation/vite): 

```
npx shadcn@latest init
```
- When prompted, choose:
    - Default styling
    - Color: `Slate`


- Start the development server:

```
npm run dev
```



# Backend 
An intelligent system that combines bank statement parsing, machine learning classification, and financial analysis to provide automated transaction categorization and spending insights.
Features

## Multi-Bank Support

- Commonwealth Bank: Full-featured parser with text alignment and multi-line transaction support
- Lloyds Bank: Payment code detection system with UK-specific date formats
- US Bank: Integrated check processing with section-based parsing
- IDFC Bank: Table-based layout parsing 
- General Parser: Fallback system with dynamic column detection for unknown formats, modeled after the Commonwealth Bank parser

## ML-Powered Transaction Classification 
The system employs a three-layer classification approach:

- Known Vendor Matching

    - Dictionary-based instant classification
    - High-precision vendor recognition


- Machine Learning Classification

    - Random Forest classifier
    - TF-IDF vectorization for transaction descriptions
    - Standardized amount scaling
    - Continuous learning from user corrections


- Pattern Detection

    - Recurring payment identification
    - Anomaly detection using IsolationForest
    - Transaction pattern analysis



## Financial Analysis 

- Category-wise spending breakdown
- Recurring payment tracking
- Unusual transaction detection
- Balance verification and reconciliation
- Comprehensive transaction history

## Installation

```
# Clone repository
git clone https://github.com/LaUrrego/casca-project.git

# Move into backend
cd backend

# Install dependencies
pip install -r requirements.txt
```

## Usage
### Starting the Server

```
uvicorn unified_backend_mvp:app --reload
```

## API Endpoints
### Process Statement

```
curl -X POST http://127.0.0.1:8000/process-statement \
    -F 'file=@statement.pdf'


Response:
{
    "statement_info": {
        "opening_balance": float,
        "closing_balance": float
    },
    "transactions": [
        {
            "date": string,
            "description": string,
            "amount": float,
            "category": string,
            "is_recurring": boolean,
            "is_unusual": boolean
        }
    ],
    "analysis": {
        "category_breakdown": object,
        "recurring_summary": object,
        "unusual_transactions": array
    }
}
```

## Update Transaction Category

```
curl -X POST http://127.0.0.1:8000/update-transaction \
     -H "Content-Type: application/json" \
     -d '{
           "transaction": {
             "check_no": "12345",
             "date": "2025-02-04",
             "description": "Payment for services",
             "amount": "100.00",
             "category": "Business Expense",
             "image_file": "receipt.jpg",
             "is_unusual": true
           }
         }'


Response:
{"message": "Model Updated!"}
```

# Technical Requirements
## Core Dependencies

- Python 3.8+
- FastAPI
- pdfplumber
- scikit-learn
- pandas
- numpy

## ML Model Requirements

- TensorFlow (optional, for future neural network implementations)
- scikit-learn 1.0+
- numpy 1.20+

# Model Training
## Initial Training
```
# Train the initial model
python ml_transaction_classifier.py

# Model automatically updates through the /update-transaction endpoint
```

# Continuous Learning
The system learns from user corrections through:

- Transaction correction submissions
- Model retraining with updated dataset
- Accuracy improvement tracking

# Current Limitations
- System is intended for submissions of original, text-based PDF documents, no scanned versions. This initial MVP is to function with the limitations of being bank worker that only has access to an initial set of 4 different statements. 
- Single transaction corrections only. Updates send user-labeled transactions and save them to the training CSV, calling the model to be retrained on the new dataset. This works fine for this current iteration, but would be slow as the dataset grows. 
- No undo function for corrections. 
- Limited currency support to handle current bank statements plus a few more. 