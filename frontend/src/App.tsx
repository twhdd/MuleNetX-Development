import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AccountSearch } from "./pages/AccountSearch";
import { AccountWorkspace } from "./pages/AccountWorkspace";
import { Audit } from "./pages/admin/Audit";
import { DatasetProfile } from "./pages/admin/DatasetProfile";
import { Ingestion } from "./pages/admin/Ingestion";
import { ModelDetail, Models } from "./pages/admin/Models";
import { PipelineDetail, Pipelines } from "./pages/admin/Pipelines";
import { Users } from "./pages/admin/Users";
import { CaseDetail } from "./pages/CaseDetail";
import { Cases } from "./pages/Cases";
import { Communities, CommunityDetail } from "./pages/Communities";
import { GraphExplorer } from "./pages/GraphExplorer";
import { Login } from "./pages/Login";
import { NotFound } from "./pages/NotFound";
import { Evaluation } from "./pages/Evaluation";
import { InterventionSimulation } from "./pages/InterventionSimulation";
import { PathView } from "./pages/PathView";
import { RingWorkspace } from "./pages/RingWorkspace";
import { Rings } from "./pages/Rings";
import { Triage } from "./pages/Triage";
import type { Role } from "./api/types";
import { useSession } from "./state/session";

function RequireSession({ children }: { children: ReactNode }) {
  const token = useSession((st) => st.token);
  const location = useLocation();
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <>{children}</>;
}

function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const role = useSession((st) => st.user?.role);
  if (!role || !roles.includes(role)) return <NotFound reason="Your role cannot open this page." />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireSession>
            <Layout />
          </RequireSession>
        }
      >
        <Route index element={<Triage />} />
        <Route path="accounts" element={<AccountSearch />} />
        <Route path="accounts/:id" element={<AccountWorkspace />} />
        <Route path="graph" element={<GraphExplorer />} />
        <Route path="paths" element={<PathView />} />
        <Route path="communities" element={<Communities />} />
        <Route path="communities/:id" element={<CommunityDetail />} />
        <Route path="rings" element={<Rings />} />
        <Route path="rings/:id" element={<RingWorkspace />} />
        <Route path="rings/:id/simulate" element={<InterventionSimulation />} />
        <Route path="evaluation" element={<Evaluation />} />
        <Route path="cases" element={<Cases />} />
        <Route path="cases/:id" element={<CaseDetail />} />
        <Route path="admin/ingestion" element={<Ingestion />} />
        <Route path="admin/datasets/:id/profile" element={<DatasetProfile />} />
        <Route path="admin/pipelines" element={<Pipelines />} />
        <Route path="admin/pipelines/:id" element={<PipelineDetail />} />
        <Route path="admin/models" element={<Models />} />
        <Route path="admin/models/:version" element={<ModelDetail />} />
        <Route path="admin/users" element={<RequireRole roles={["ADMIN"]}><Users /></RequireRole>} />
        <Route path="admin/audit" element={<RequireRole roles={["ADMIN"]}><Audit /></RequireRole>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
