# MemCloud Console - Frontend

Beautiful Next.js 14 dashboard for deploying MemMachine to GCP.

## Features

- 🚀 One-click MemMachine deployment
- 📊 Instance management dashboard
- 🎨 Beautiful Vercel-style UI
- ⚡ Real-time deployment status
- 📱 Mobile responsive

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Landing page
│   ├── dashboard/
│   │   └── page.tsx          # Dashboard with deploy button
│   ├── layout.tsx            # Root layout
│   └── globals.css           # Global styles
├── components/               # Reusable components
├── lib/
│   ├── api.ts               # API client
│   └── utils.ts             # Utility functions
└── public/                  # Static assets
```

## Deployment to Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/memmachine-cloud/memcloud-console
gcloud run deploy memcloud-console \
  --image gcr.io/memmachine-cloud/memcloud-console \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars NEXT_PUBLIC_API_URL=https://memcloud-api-xyz.run.app
```

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Icons:** Lucide React
- **Deployment:** Cloud Run
