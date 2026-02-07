# BotSetu 🤖

**WhatsApp Bot Builder for Small Business**

Create intelligent WhatsApp bots without coding. Automate customer support, sales, and engagement for your small business.

## 🚀 Features

- **🧾 Business Management** - Configure business details, hours, and location
- **🤖 Bot Configuration** - Set up bot behavior, auto-reply, and human handoff
- **📞 WhatsApp Integration** - Connect with Twilio, Infobip, or other BSP providers
- **📝 Template Management** - Create and manage message templates
- **💬 Conversation Flows** - Design custom conversation flows for different use cases
- **💰 Flexible Billing** - Choose from Free, Starter, Pro, or Enterprise plans
- **🔐 Secure Authentication** - Powered by Clerk for user management
- **📊 Multi-step Form** - Intuitive step-by-step bot creation process with progress tracking

## 🛠️ Tech Stack

### Frontend
- **Next.js 16** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **Clerk** - Authentication and user management
- **Radix UI** - Accessible UI components
- **Lucide Icons** - Beautiful icon library

### Backend
- **MongoDB** - NoSQL database for bot data storage
- **Next.js API Routes** - Serverless API endpoints

## 📋 Prerequisites

- Node.js 18+ and npm
- MongoDB (local or cloud instance)
- Clerk account ([clerk.com](https://clerk.com))
- Git

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/chiman45/BotSetu.git
cd BotSetu
```

### 2. Install Frontend dependencies

```bash
cd Frontend
npm install --legacy-peer-deps
```

### 3. Set up environment variables

Create a `.env.local` file in the `Frontend` directory:

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_publishable_key
CLERK_SECRET_KEY=your_secret_key

# MongoDB Connection
MONGODB_URI=mongodb://localhost:27017/
```

**Get your Clerk keys:**
1. Go to [Clerk Dashboard](https://dashboard.clerk.com/)
2. Create a new application or select existing
3. Navigate to API Keys
4. Copy your Publishable Key and Secret Key

### 4. Start MongoDB

Make sure MongoDB is running on your local machine:

```bash
mongod
```

Or use MongoDB Atlas for a cloud database.

### 5. Run the development server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
BotSetu/
├── Backend/
│   ├── attach.py                    # WhatsApp number attachment service
│   ├── creation.py                  # Twilio subaccount management
│   ├── requirements.txt             # Python dependencies
│   ├── INTEGRATION_GUIDE.md         # Backend integration guide
│   ├── README.md                    # Backend documentation
│   └── .env                         # Backend environment variables
├── Frontend/
│   ├── app/
│   │   ├── about/
│   │   │   └── page.tsx             # About page
│   │   ├── api/
│   │   │   └── bot/
│   │   │       └── route.ts         # Bot API endpoints
│   │   ├── create/
│   │   │   └── page.tsx             # Multi-step bot creation form
│   │   ├── dashboard/
│   │   │   └── page.tsx             # User dashboard
│   │   ├── payment/
│   │   │   └── page.tsx             # Payment page
│   │   ├── pricing/
│   │   │   └── page.tsx             # Pricing plans page
│   │   ├── globals.css              # Global styles
│   │   ├── layout.tsx               # Root layout with Clerk
│   │   ├── page.tsx                 # Landing page
│   │   └── favicon.ico              # Site favicon
│   ├── components/
│   │   └── ui/
│   │       └── button.tsx           # Reusable button component
│   ├── images/
│   │   └── bg.avif                  # Background image
│   ├── lib/
│   │   ├── mongodb.ts               # MongoDB connection
│   │   └── utils.ts                 # Utility functions
│   ├── public/                      # Static assets
│   ├── middleware.ts                # Clerk middleware
│   ├── components.json              # shadcn/ui config
│   ├── next.config.ts               # Next.js configuration
│   ├── tsconfig.json                # TypeScript config
│   ├── package.json                 # Dependencies
│   └── .env.local                   # Frontend environment variables
├── DOCKER_GUIDE.md                  # Docker setup guide
├── docker-compose.yml               # Docker compose configuration
├── Dockerfile.backend               # Backend Docker image
├── Dockerfile.frontend              # Frontend Docker image
└── README.md                        # Project documentation
```

## 🎯 Usage

### Creating a Bot

1. **Sign Up/Login** - Click "Join" or "Login" on the homepage
2. **Create Bot** - Click "Create Your Bot Now"
3. **Follow the Steps:**
   - 🧾 **Business Info** - Enter business details
   - 🤖 **Bot Config** - Configure bot settings
   - 📞 **WhatsApp Setup** - Add WhatsApp integration details
   - 📝 **Templates** - Create message templates (optional)
   - 💬 **Conversation** - Set up conversation flows (optional)
   - 💰 **Billing** - Select your plan
4. **Submit** - Your bot configuration is saved to MongoDB

### Data Storage

All bot configurations are stored in MongoDB:
- **Database:** `BotSetu`
- **Collection:** `User-data`
- **Fields:** Business info, bot config, WhatsApp setup, templates, conversations, billing, and ownership

## 🔑 Key Features Explained

### Multi-step Form with Progress Tracking
- Visual timeline showing current step
- Green checkmarks for completed steps
- Step validation before proceeding
- Smooth animations between steps

### Clerk Authentication
- Modal-based sign-in/sign-up
- User session management
- Protected routes via middleware
- User profile with UserButton

### MongoDB Integration
- Automatic business ID generation
- User ownership tracking
- Timestamps for created/updated records
- Efficient data retrieval

## 🚧 Roadmap

- [ ] Dashboard to view all created bots
- [ ] Bot analytics and metrics
- [ ] WhatsApp message testing
- [ ] Template approval workflow
- [ ] Conversation flow builder (drag-and-drop)
- [ ] Multi-language support
- [ ] Payment integration
- [ ] Webhook configuration
- [ ] Real-time chat preview

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 👨‍💻 Author

**Chiman**
- GitHub: [@chiman45](https://github.com/chiman45)

## 🙏 Acknowledgments

- [Next.js](https://nextjs.org/)
- [Clerk](https://clerk.com/)
- [MongoDB](https://www.mongodb.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Radix UI](https://www.radix-ui.com/)

---

Built with ❤️ for small businesses looking to automate WhatsApp communication
