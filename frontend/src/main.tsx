import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { ROLE_HOME } from "./api";
import Layout from "./Layout";
import { LoginPage, SignupPage } from "./pages/Auth";
import { BillsPage } from "./pages/Bills";
import { InvestorBoardPage, SupplierBoardPage } from "./pages/Board";
import { EoiDraftPage, ProposalDraftPage } from "./pages/Documents";
import { InvestorListingPage, SupplierListingPage } from "./pages/ListingDetail";
import {
  ActivityPage,
  BillingPage,
  InvestorConnectionsPage,
  SupplierLeadsPage,
  SupplierRequestsPage,
  WalletPage,
} from "./pages/Partners";
import { SmeListingPage, SmeRequestsPage } from "./pages/Sme";
import { SessionProvider, useSession } from "./session";

function Home() {
  const { role } = useSession();
  return <Navigate to={ROLE_HOME[role]} replace />;
}

function RequireSignIn() {
  const { signedIn } = useSession();
  return signedIn ? <Layout /> : <Navigate to="/login" replace />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SessionProvider>
      <BrowserRouter basename="/app">
        <Routes>
          <Route path="login" element={<LoginPage />} />
          <Route path="signup" element={<SignupPage />} />
          <Route element={<RequireSignIn />}>
            <Route index element={<Home />} />
            <Route path="sme/bills" element={<BillsPage />} />
            <Route path="sme/listing" element={<SmeListingPage />} />
            <Route path="sme/requests" element={<SmeRequestsPage />} />
            <Route path="sme/activity" element={<ActivityPage />} />
            <Route path="sme/wallet" element={<WalletPage />} />
            <Route path="investor/board" element={<InvestorBoardPage />} />
            <Route path="investor/listing/:id" element={<InvestorListingPage />} />
            <Route path="investor/connections" element={<InvestorConnectionsPage />} />
            <Route path="investor/eoi/:requestId" element={<EoiDraftPage />} />
            <Route path="investor/billing" element={<BillingPage />} />
            <Route path="supplier/board" element={<SupplierBoardPage />} />
            <Route path="supplier/listing/:id" element={<SupplierListingPage />} />
            <Route path="supplier/proposal/:listingId" element={<ProposalDraftPage />} />
            <Route path="supplier/requests" element={<SupplierRequestsPage />} />
            <Route path="supplier/leads" element={<SupplierLeadsPage />} />
            <Route path="supplier/billing" element={<BillingPage />} />
            <Route path="ops/audit" element={<ActivityPage title="Audit log" />} />
            <Route path="*" element={<Home />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SessionProvider>
  </StrictMode>,
);
