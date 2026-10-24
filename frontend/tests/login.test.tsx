import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useSession } from "../src/state/session";
import { renderAt } from "./render";

describe("login (T25)", () => {
  it("redirects to login without a session, signs in, and keeps the token in memory only", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const { user } = renderAt("/accounts");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Username"), "inv");
    await user.type(screen.getByLabelText("Password"), "right-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByLabelText("Active analytical context")).toBeInTheDocument();
    expect(useSession.getState().token).toBe("tok-123");
    expect(setItem).not.toHaveBeenCalled();
  });

  it("shows a precise message on bad credentials", async () => {
    const { user } = renderAt("/login");
    await user.type(screen.getByLabelText("Username"), "inv");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Username or password is incorrect");
    await waitFor(() => expect(useSession.getState().token).toBeNull());
  });
});
