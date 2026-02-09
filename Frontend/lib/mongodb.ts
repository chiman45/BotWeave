import { MongoClient } from 'mongodb';

// Allow build to proceed without MongoDB URI (for static pages)
// But runtime API calls will still fail if not provided
if (!process.env.MONGODB_URI && process.env.NODE_ENV !== 'production') {
  console.warn('⚠️  Warning: MONGODB_URI not set. API routes will not work.');
}

const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/BotSetu';
const options = {};

let client: MongoClient;
let clientPromise: Promise<MongoClient>;

if (process.env.NODE_ENV === 'development') {
  // In development mode, use a global variable so that the value
  // is preserved across module reloads caused by HMR (Hot Module Replacement).
  let globalWithMongo = global as typeof globalThis & {
    _mongoClientPromise?: Promise<MongoClient>;
  };

  if (!globalWithMongo._mongoClientPromise) {
    client = new MongoClient(uri, options);
    globalWithMongo._mongoClientPromise = client.connect();
  }
  clientPromise = globalWithMongo._mongoClientPromise;
} else {
  // In production mode, it's best to not use a global variable.
  client = new MongoClient(uri, options);
  clientPromise = client.connect();
}

export default clientPromise;
