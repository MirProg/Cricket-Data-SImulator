import "./globals.css";
import Link from "next/link";
import Sidebar from "../components/Sidebar";
import Searchbar from "../components/Searchbar";

export const metadata = {
  title: "Cricket Database Portal",
  description: "Massive cricket statistics database and AI Simulator",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen flex flex-col font-sans">
        {/* Global Navigation Bar */}
        <nav className="w-full bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <Link href="/" className="flex-shrink-0 text-xl font-black text-blue-700">
                  CRICDB
                </Link>
                <div className="hidden md:block ml-10">
                  <div className="flex items-baseline space-x-6">
                    <Link href="/" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-semibold transition-colors">
                      Home
                    </Link>
                    <Link href="/records" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-semibold transition-colors">
                      Records
                    </Link>
                    <Link href="/archive" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-semibold transition-colors">
                      True Archive
                    </Link>
                    <Link href="/simulator" className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-semibold transition-colors">
                      AI Simulator
                    </Link>
                    <Link href="/custom-match" className="text-gray-600 hover:text-emerald-600 px-3 py-2 rounded-md text-sm font-semibold transition-colors">
                      Custom Match
                    </Link>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <Searchbar />
              </div>
            </div>
          </div>
        </nav>

        {/* Page Content with Sidebar */}
        <div className="flex flex-grow w-full max-w-7xl mx-auto">
          <Sidebar />
          <main className="flex-grow w-full lg:ml-6 min-h-screen pb-12">
            {children}
          </main>
        </div>
        
        {/* Footer */}
        <footer className="w-full bg-white border-t border-gray-200 py-6 text-center text-gray-500 text-sm mt-auto">
          &copy; {new Date().getFullYear()} CricDB Portal. Professional Cricket Statistics Engine.
        </footer>
      </body>
    </html>
  );
}
