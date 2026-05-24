package clio.router.entitlements;

import clio.core.Application;
import clio.core.Strings;
import org.junit.Test;

import static org.junit.Assert.assertThrows;

public class TestEntitlements {

    private static final String mockEntitlements =
"""
{
  "patterns": {
    "all": ".*",
    "elevated": "^restricted\\\\..*"
  },

  "groups": {
    "denied": [
      { "pattern": "all", "grant": false}
    ],
    "standard": [
      { "pattern": "elevated", "grant": false},
      { "pattern": "all", "grant": true}
    ],
    "elevated": [
      { "pattern": "elevated", "grant": true}
    ]
  },

  "users" : {
    "_default": ["denied"],
    "standard_user": ["standard"],
    "elevated_user": ["elevated", "standard"]
  }
}
""";

    @Test
    public void testEntitlements() {
        var entitlements = new Entitlements(Strings.readJson(mockEntitlements, EntitlementsDfn.class));

        entitlements.check("standard_user", "a command");
        assertThrows(Exception.class, () -> entitlements.check("unknown", "a command"));

        entitlements.check("elevated_user", "restricted.command ...");
        assertThrows(Exception.class, () -> entitlements.check("standard_user", "restricted.command ..."));
    }
}
