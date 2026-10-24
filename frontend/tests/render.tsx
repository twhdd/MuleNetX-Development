import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../src/App";
import type { Role } from "../src/api/types";
import { useSession } from "../src/state/session";

export function signIn(role: Role = "INVESTIGATOR", userId = "u-investigator") {
  useSession.getState().signIn("tok-123", { user_id: userId, username: `${role.toLowerCase()}1`, role }, 3600);
}

export function renderAt(path: string) {
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  return { user, ...view };
}
