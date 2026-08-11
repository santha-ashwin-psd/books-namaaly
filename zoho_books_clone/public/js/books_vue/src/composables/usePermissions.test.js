// Tests for usePermissions() (composables/usePermissions.js) -- the
// frontend mirror of utils/access.py's _membership()/can_*() logic.
//
// This is Phase 8 of the test coverage audit: the app had zero automated
// frontend tests before this file, including for the permission-gating
// composable used to hide/disable buttons across every module page.
//
// `session` (api/session.js) is a plain Vue `reactive()` singleton, so
// tests mutate `session.permissions` directly rather than mocking the
// module -- simpler and exercises the real reactivity path.
//
// Run with: npm test  (or: npx vitest run)

import { describe, it, expect, beforeEach } from "vitest";
import { session } from "../api/session.js";
import { usePermissions } from "./usePermissions.js";

function resetSession() {
  session.permissions = {
    books_role: "Accountant",
    is_company_admin: false,
    read_only: false,
    levels: {},
  };
}

beforeEach(resetSession);

describe("isAdmin / isReadonly / role / flags", () => {
  it("isAdmin reflects is_company_admin", () => {
    session.permissions.is_company_admin = true;
    const { isAdmin } = usePermissions();
    expect(isAdmin.value).toBe(true);
  });

  it("isReadonly true when server read_only flag is set", () => {
    session.permissions.read_only = true;
    const { isReadonly } = usePermissions();
    expect(isReadonly.value).toBe(true);
  });

  it("isReadonly falls back to books_role for older sessions without read_only", () => {
    delete session.permissions.read_only;
    session.permissions.books_role = "Books Viewer";
    const { isReadonly } = usePermissions();
    expect(isReadonly.value).toBe(true);
  });

  it("isReadonly false for a normal role with no read_only flag", () => {
    session.permissions.books_role = "Accountant";
    session.permissions.read_only = false;
    const { isReadonly } = usePermissions();
    expect(isReadonly.value).toBe(false);
  });

  it("role reflects books_role", () => {
    session.permissions.books_role = "Books Manager";
    const { role } = usePermissions();
    expect(role.value).toBe("Books Manager");
  });

  it("role empty string when permissions not yet loaded", () => {
    session.permissions = {};
    const { role, isAdmin } = usePermissions();
    expect(role.value).toBe("");
    expect(isAdmin.value).toBe(false);
  });

  it("flags exposes the raw permissions object", () => {
    session.permissions.mod_invoices = true;
    const { flags } = usePermissions();
    expect(flags.value.mod_invoices).toBe(true);
  });
});

describe("can(module)", () => {
  it("returns true for a falsy module (unmapped route, e.g. dashboard)", () => {
    const { can } = usePermissions();
    expect(can(null)).toBe(true);
    expect(can("")).toBe(true);
    expect(can(undefined)).toBe(true);
  });

  it("admin gets every module regardless of levels", () => {
    session.permissions.is_company_admin = true;
    session.permissions.levels = { invoices: "None" };
    const { can } = usePermissions();
    expect(can("invoices")).toBe(true);
  });

  it("level 'None' (explicit) blocks the module", () => {
    session.permissions.levels = { invoices: "None" };
    const { can } = usePermissions();
    expect(can("invoices")).toBe(false);
  });

  it("missing level entry defaults to None and blocks", () => {
    session.permissions.levels = {};
    const { can } = usePermissions();
    expect(can("invoices")).toBe(false);
  });

  it.each(["View", "Create", "Edit", "Delete"])(
    "any non-None level ('%s') allows the module",
    (level) => {
      session.permissions.levels = { invoices: level };
      const { can } = usePermissions();
      expect(can("invoices")).toBe(true);
    },
  );
});

describe("canWrite(module)", () => {
  it("admin can always write", () => {
    session.permissions.is_company_admin = true;
    session.permissions.read_only = true; // even if also flagged read-only
    session.permissions.levels = { invoices: "None" };
    const { canWrite } = usePermissions();
    expect(canWrite("invoices")).toBe(true);
  });

  it("readonly role cannot write even if the module level is granted", () => {
    session.permissions.read_only = true;
    session.permissions.levels = { invoices: "Edit" };
    const { canWrite } = usePermissions();
    expect(canWrite("invoices")).toBe(false);
  });

  it("non-readonly member with the module on can write", () => {
    session.permissions.read_only = false;
    session.permissions.levels = { invoices: "Edit" };
    const { canWrite } = usePermissions();
    expect(canWrite("invoices")).toBe(true);
  });

  it("non-readonly member without the module cannot write", () => {
    session.permissions.read_only = false;
    session.permissions.levels = { invoices: "None" };
    const { canWrite } = usePermissions();
    expect(canWrite("invoices")).toBe(false);
  });
});

describe("levelOf(module)", () => {
  it("admin always resolves to Delete, the highest tier", () => {
    session.permissions.is_company_admin = true;
    session.permissions.levels = { invoices: "None" };
    const { levelOf } = usePermissions();
    expect(levelOf("invoices")).toBe("Delete");
  });

  it("non-admin reads the module's actual level", () => {
    session.permissions.levels = { invoices: "Create" };
    const { levelOf } = usePermissions();
    expect(levelOf("invoices")).toBe("Create");
  });

  it("missing level entry defaults to None", () => {
    session.permissions.levels = {};
    const { levelOf } = usePermissions();
    expect(levelOf("invoices")).toBe("None");
  });
});

describe("canCreate / canEdit / canDelete threshold gating", () => {
  it("admin passes every gate regardless of levels", () => {
    session.permissions.is_company_admin = true;
    session.permissions.levels = { invoices: "None" };
    const { canCreate, canEdit, canDelete } = usePermissions();
    expect(canCreate("invoices")).toBe(true);
    expect(canEdit("invoices")).toBe(true);
    expect(canDelete("invoices")).toBe(true);
  });

  it("level 'None' blocks all three gates", () => {
    session.permissions.levels = { invoices: "None" };
    const { canCreate, canEdit, canDelete } = usePermissions();
    expect(canCreate("invoices")).toBe(false);
    expect(canEdit("invoices")).toBe(false);
    expect(canDelete("invoices")).toBe(false);
  });

  it("level 'View' allows none of create/edit/delete", () => {
    session.permissions.levels = { invoices: "View" };
    const { canCreate, canEdit, canDelete } = usePermissions();
    expect(canCreate("invoices")).toBe(false);
    expect(canEdit("invoices")).toBe(false);
    expect(canDelete("invoices")).toBe(false);
  });

  it("level 'Create' allows create only", () => {
    session.permissions.levels = { invoices: "Create" };
    const { canCreate, canEdit, canDelete } = usePermissions();
    expect(canCreate("invoices")).toBe(true);
    expect(canEdit("invoices")).toBe(false);
    expect(canDelete("invoices")).toBe(false);
  });

  it("level 'Edit' allows create and edit, not delete", () => {
    session.permissions.levels = { invoices: "Edit" };
    const { canCreate, canEdit, canDelete } = usePermissions();
    expect(canCreate("invoices")).toBe(true);
    expect(canEdit("invoices")).toBe(true);
    expect(canDelete("invoices")).toBe(false);
  });

  it("level 'Delete' allows all three", () => {
    session.permissions.levels = { invoices: "Delete" };
    const { canCreate, canEdit, canDelete } = usePermissions();
    expect(canCreate("invoices")).toBe(true);
    expect(canEdit("invoices")).toBe(true);
    expect(canDelete("invoices")).toBe(true);
  });

  it("levels are per-module -- a grant on one module doesn't leak to another", () => {
    session.permissions.levels = { invoices: "Delete", bills: "None" };
    const { canDelete } = usePermissions();
    expect(canDelete("invoices")).toBe(true);
    expect(canDelete("bills")).toBe(false);
  });
});

describe("reactivity", () => {
  it("computed values update after session.permissions changes, without re-calling usePermissions()", () => {
    session.permissions.levels = { invoices: "None" };
    const { canEdit } = usePermissions();
    expect(canEdit("invoices")).toBe(false);

    session.permissions.levels.invoices = "Edit";
    expect(canEdit("invoices")).toBe(true);
  });
});