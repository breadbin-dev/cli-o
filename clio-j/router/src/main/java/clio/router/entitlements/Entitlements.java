package clio.router.entitlements;

import clio.core.Collections;
import clio.core.Strings;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static clio.core.Strings.f;

public class Entitlements {

    public record Rule(Pattern pattern, boolean grant){}

    private final Map<String, List<Rule>> rules = new HashMap<>();

    private final List<Rule> defaults;

    public Entitlements(InputStream file) {
        this(Strings.readJson(file, EntitlementsDfn.class));
    }

    public Entitlements(EntitlementsDfn dfn) {
        var patterns = Collections.map(dfn.patterns(), (k, v) -> Pattern.compile(v));
        var groups = Collections.map(dfn.groups(), (k, v) -> Collections.map(v, i -> new Rule(Collections.ensure(patterns, i.pattern()), i.grant())));
        for (var e : dfn.users().entrySet()) {
            var user = e.getKey();
            if ("$SYSTEM_USER".equals(user))
                user = System.getProperty("user.name");
            var rules = this.rules.computeIfAbsent(user, k -> new ArrayList<>());
            for (var rule : e.getValue())
                rules.addAll(Collections.ensure(groups, rule));
        }
        defaults = Collections.ensure(this.rules, "_default");
    }

    public void check(String user, String command) {
        var rules = this.rules.get(user);
        if (rules == null)
            rules = this.defaults;

        for (var r : rules) {
            if (r.pattern().matcher(command).matches()) {
                if (r.grant())
                    return;
                throw new RuntimeException(f("[{}] access denied", user));
            }
        }

        throw new RuntimeException(f("[{}] access denied: {}", user, command));
    }
}
