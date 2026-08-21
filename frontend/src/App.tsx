import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "./auth";
import Login from "./pages/Login";
import PatientDetail from "./pages/PatientDetail";
import Patients from "./pages/Patients";
import Review from "./pages/Review";
import Signup from "./pages/Signup";

const queryClient = new QueryClient();

function Protected({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/patients"
              element={
                <Protected>
                  <Patients />
                </Protected>
              }
            />
            <Route
              path="/patients/:id"
              element={
                <Protected>
                  <PatientDetail />
                </Protected>
              }
            />
            <Route
              path="/review"
              element={
                <Protected>
                  <Review />
                </Protected>
              }
            />
            <Route path="*" element={<Navigate to="/patients" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
