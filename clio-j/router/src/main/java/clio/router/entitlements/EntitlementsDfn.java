package clio.router.entitlements;

import java.util.List;
import java.util.Map;

public record EntitlementsDfn(Map<String, String> patterns, Map<String, List<EntitlementRule>> groups, Map<String, List<String>> users) {
}

record EntitlementRule(String pattern, boolean grant) {}
