package clio.core.db;

import clio.core.Collections;
import clio.core.Dttms;
import clio.core.Strings;

import java.lang.reflect.InvocationTargetException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static clio.core.Strings.f;

public class Databases {
    private final static String tableTemplate = """
-- *** {table_name} ***

-- drop table {table_name};

create table if not exists {table_name}
(
{table_columns}
)
    engine = MergeTree()
    partition by toYYYYMM({dttm_column})
    order by ({table_keys})
    comment 'auto generated table';

select * from {table_name} limit 10;

-- migrators
{insert_columns}

    """;

    static Set<String> nullableFields(Class<?> cls) throws IllegalAccessException, InvocationTargetException {
        try {
            return new HashSet<>((List<String>)cls.getDeclaredMethod("nullable").invoke(null));
        } catch (NoSuchMethodException ex) {
            return Collections.emptySet();
        }
    }

    static String dttmField(Class<?> cls) throws IllegalAccessException, InvocationTargetException {
        try {
            return (String)cls.getDeclaredMethod("dttmField").invoke(null);
        } catch (NoSuchMethodException ex) {
            return "dttm";
        }
    }

    public static String insertColumn(String table, String cf, String prev) {
        cf = cf.trim();

        if (prev == null)
            return f("-- alter table {} add column {};", table, cf);
        else
            return f("-- alter table {} add column {} after {};", table, cf, prev);
    }

    public static String tableForCls(Class<?> cls) {
        try {
            var table = Strings.camelToSnake(cls.getSimpleName());
            var columns = new ArrayList<String>();
            var nullable = nullableFields(cls);
            var dttmField = dttmField(cls);
            var insertColumns = new ArrayList<String>();

            String prev = null;
            for (var field : cls.getDeclaredFields()) {
                var name = Strings.camelToSnake(field.getName());
                var cf = columnForField(name, field.getType(), nullable.contains(field.getName()));
                columns.add(cf);
                insertColumns.add(insertColumn(table, cf, prev));
                prev = name;
            }

            var keys = new ArrayList<String>();
            keys.add(dttmField);
            keys.addAll(keysForCls(cls));

            return tableTemplate
                    .replace("{table_name}", table)
                    .replace("{table_columns}", String.join(",\n", columns))
                    .replace("{table_keys}", String.join(", ", keys))
                    .replace("{dttm_column}", dttmField)
                    .replace("{insert_columns}", String.join("\n", insertColumns));
        }
        catch (IllegalAccessException | InvocationTargetException e) {
            throw new RuntimeException(e);
        }
    }

    public static List<String> keysForCls(Class<?> cls) {
        try {
            return (List<String>) cls.getDeclaredMethod("keys").invoke(null);
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static String typeForField(Class<?> cls) {
        if (cls == LocalDate.class)
            return "Date";
        if (cls == LocalDateTime.class)
            return "DateTime64(9)";
        if (cls == String.class || cls.isEnum())
            return "String";
        if (cls == Double.class || cls == double.class)
            return "Float64";
        if (cls == Integer.class || cls == int.class || cls == Long.class || cls == long.class)
            return "Int64";
        if (cls == Boolean.class || cls == boolean.class)
            return "Boolean";

        throw new RuntimeException(f("Unsupported type {}", cls.getSimpleName()));
    }

    public static String columnForField(String name, Class<?> cls, boolean nullable) {
        var t = typeForField(cls);
        if (nullable)
            t = "Nullable(" + t + ")";
        return f("    {} {}", name, t);
    }

    public static String filterDttm(LocalDateTime dttm) {
        return "toDateTime64('" + Dttms.formatSql(dttm) + "', 9)";
    }
}
