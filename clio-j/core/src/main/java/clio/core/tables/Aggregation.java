package clio.core.tables;

import java.util.function.BiConsumer;
import java.util.regex.Pattern;

public interface Aggregation {
    Pattern pattern = Pattern.compile("^([^(]+)(?:\\(([^)]*)\\))?$");

    String target();
    void aggregate(Table table, BiConsumer<Object, Object> result);

    static Aggregation parse(String aggStr) {
        var m = pattern.matcher(aggStr);
        if (!m.matches())
            throw new RuntimeException("Unable to parse aggregation [" + aggStr + "]");

        var func = m.group(1);
        var args  = m.group(2);

        return switch (func) {
            case "sum" -> Sum.of(args);
            case "count" -> Count.of(args);
            default -> throw new RuntimeException("Unknown function [" + func + "]");
        };
    }

    static Aggregation[] parseList(String aggsStr) {
        var strs = aggsStr.split("\\|");
        var result = new Aggregation[strs.length];
        for (var i = 0; i < strs.length; i++)
            result[i] = parse(strs[i]);
        return result;
    }
}
