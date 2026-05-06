package clio.core.tables;

import clio.core.Strings;

import java.util.function.BiConsumer;

public class Count implements Aggregation {

    static Count of(String arg) {
        return Strings.hasValue(arg) ? new Count(arg) : new Count();
    }


    private final String target;

    public Count() {
        this("count");
    }

    public Count(String target) {
        this.target = target;
    }

    @Override
    public String target() {
        return target;
    }

    @Override
    public void aggregate(Table table, BiConsumer<Object, Object> result) {
        result.accept(target, table.size());
    }
}
