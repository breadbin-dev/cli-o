package clio.core.tables;

import java.util.function.BiConsumer;

public class Sum implements Aggregation {

    static Sum of(String arg) {
        var args = arg.split(",");
        if (args.length == 1)
            return new Sum(args[0]);
        if (args.length == 2)
            return new Sum(args[0], args[1]);
        throw new RuntimeException("Invalid args: "+arg);
    }

    private final String target;
    private final String source;

    public Sum(String source) {
        this("sum", source);
    }

    public Sum(String target, String source) {
        this.target = target;
        this.source = source;
    }

    @Override
    public String target() {
        return target;
    }

    @Override
    public void aggregate(Table table, BiConsumer<Object, Object> result) {
        if (table.isEmpty())
            result.accept(target, 0);
        else {
            var col = table.column(source);
            var rows = table.rows();
            var cls = rows.iterator().next().read(col).getClass();
            if (cls == Double.class)
                result.accept(target, sumDouble(rows, col));
            else if (cls == Integer.class)
                result.accept(target, sumInt(rows, col));
            else if (cls == Long.class)
                result.accept(target, sumLong(rows, col));
            else
                throw new RuntimeException("Unsupported: " + cls.getName());
        }
    }

    private Double sumDouble(Iterable<? extends Row> rows, Column source) {
        var sum = 0.0;
        for (var r : rows)
            sum += r.readDouble(source);
        return sum;
    }

    private Integer sumInt(Iterable<? extends Row> rows, Column source) {
        var sum = 0;
        for (var r : rows)
            sum += r.readInt(source);
        return sum;
    }

    private Long sumLong(Iterable<? extends Row> rows, Column source) {
        var sum = 0L;
        for (var r : rows)
            sum += r.readLong(source);
        return sum;
    }
}
