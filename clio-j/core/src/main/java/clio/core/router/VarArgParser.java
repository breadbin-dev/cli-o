package clio.core.router;

import org.apache.logging.log4j.util.Strings;

import java.util.*;

public class VarArgParser implements ArgParser<Map<String, Object>> {
    /*
    without context, infer args from strings
     */
    @Override
    public Map<String, Object> parse(String args) {
        var result = new HashMap<String, Object>();
        String name = null;
        Set<Object> values = null;
        for (var token : args.split(" ")) {
            if (Strings.isEmpty(token))
                continue;

            if (token.startsWith("--")) {
                if (name != null) {
                    result.put(name, value(values));
                    values = null;
                }
                name = token.substring(2);
            }
            else if (token.startsWith("-")) {
                throw new RuntimeException("short options not supported: " + token);
            } else {
                if (name == null)
                    throw new RuntimeException("unexpected option without name: " + token);

                if (values == null)
                    values = new HashSet<>();

                values.add(token(token));
            }
        }
        if (name != null) {
            result.put(name, value(values));
        }

        return result;
    }

    private Object value(Object value) {
        if (value == null)
            return true;
        if (value instanceof Set<?> set && set.size() == 1)
            return set.iterator().next();
        return value;
    }

    private Object token(String token) {
        if (token.chars().allMatch(Character::isDigit))
            return Long.parseLong(token);
        if (token.chars().allMatch(c -> Character.isDigit(c) || c == '.'))
            return Double.parseDouble(token);
        if (token.startsWith("\"") && token.endsWith("\""))
            return token.substring(1, token.length() - 1);
        return token;
    }
}
