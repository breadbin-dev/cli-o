package clio.core;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.json.JsonReadFeature;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.fasterxml.jackson.datatype.jsr310.ser.ZonedDateTimeSerializer;
import org.slf4j.helpers.MessageFormatter;

import java.io.*;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.function.Supplier;
import java.util.regex.Pattern;

public class Strings {

    private static final String randomChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

    private static final Pattern varPattern = Pattern.compile("\\$\\{[^}]+}");

    private static final ObjectMapper json;

    static {
        var timeModule = new JavaTimeModule();
        timeModule.addSerializer(ZonedDateTime.class, new ZonedDateTimeSerializer(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssX")));

        json = JsonMapper.builder()
                .enable(JsonReadFeature.ALLOW_NON_NUMERIC_NUMBERS)
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
                .serializationInclusion(JsonInclude.Include.NON_NULL)
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
                .build();

        json.registerModule(timeModule);
    }

    public static boolean hasValue(String maybeNullOrEmpty) {
        return maybeNullOrEmpty != null && !maybeNullOrEmpty.isEmpty();
    }

    public static String random(int len) {
        var random = new SecureRandom();
        var str = new char[len];
        for (var i = 0; i < len; i++)
            str[i] = randomChars.charAt(random.nextInt(randomChars.length()));
        return new String(str);
    }

    public static String timeCode(LocalDateTime dttm, int size) {
        // string that changes through time, safe way of ensuring uniqueness across service restarts

        if (size > 7)
            throw new RuntimeException("Out of range");

        var start = LocalDateTime.of(2000, 1, 1, 0, 0).toInstant(ZoneOffset.UTC).toEpochMilli();
        var end = LocalDateTime.of(2050, 1, 1, 0, 0).toInstant(ZoneOffset.UTC).toEpochMilli();
        var now = dttm.toInstant(ZoneOffset.UTC).toEpochMilli();

        var total = end - start;
        var max = Numbers.longPow(randomChars.length(), size);
        var range = (total / max) + 1;

        var x = ((now - start) % total) / range;
        var code = new char[size];
        for (var i = 0; i < size; i++) {
            code[i] = randomChars.charAt((int)(x % randomChars.length()));
            x /= randomChars.length();
        }
        return new String(code);
    }

    public static String f(String fmt, Object arg) {
        return MessageFormatter.format(fmt, arg).getMessage();
    }

    public static String f(String fmt, Object arg1, Object arg2) {
        return MessageFormatter.format(fmt, arg1, arg2).getMessage();
    }

    public static String f(String fmt, Object... args) {
        return MessageFormatter.arrayFormat(fmt, args).getMessage();
    }

    public static String fs(String fmt, Object... args) {
        return String.format(fmt, args);
    }

    public static <T> T readJsonFile(String file, Class<T> cls) {
        return readJson(new File(file), cls);
    }

    public static <T> T readJsonFile(String file, TypeReference<T> cls) {
        return readJson(new File(file), cls);
    }

    public static <T> T readJson(InputStream is, TypeReference<T> cls) {
        try {
            return json.readValue(is, cls);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T readJson(File file, TypeReference<T> cls) {
        try {
            return json.readValue(file, cls);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T readJson(File file, Class<T> cls) {
        try {
            return json.readValue(file, cls);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T readJson(String jsonStr, Class<T> cls) {
        try {
            return json.readValue(jsonStr, cls);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T readJson(InputStream is, Class<T> cls) {
        try {
            return json.readValue(is, cls);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static void writeJsonFile(String file, Object obj) {
        writeJson(new File(file), obj);
    }

    public static void writeJson(File file, Object obj) {
        try {
            json.writeValue(file, obj);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static String toJson(Object obj) {
        try {
            return json.writeValueAsString(obj);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static String camelToSnake(String input) {
        if (input == null || input.isEmpty())
            return input;

        var output = new StringBuilder();
        for (var i = 0; i < input.length(); i++) {
            var ch = input.charAt(i);
            if (Character.isUpperCase(ch)) {
                if (i > 0)
                    output.append('_');
                output.append(Character.toLowerCase(ch));
            }
            else {
                output.append(ch);
            }
        }

        return output.toString();
    }

    public static void writeFile(String content, String file) {
        try {
            Files.writeString(Path.of(file), content);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static Iterator<String> readStreamLines(InputStream stream) {
        var reader = new BufferedReader(new InputStreamReader(stream));

        var i = new Iterator<String>()
        {
            private String next;

            public boolean hasNext()
            {
                return next != null;
            }

            public String next()
            {
                try {
                    var yield = next;
                    next = reader.readLine();
                    return yield;
                }
                catch (IOException e) {
                    throw new RuntimeException(e);
                }
            }
        };
        i.next();
        return i;
    }

    public static String readStream(InputStream stream) {
        return readStream(stream, StandardCharsets.UTF_8);
    }

    public static String readStream(InputStream stream, Charset encoding) {
        try {
            var result = new ByteArrayOutputStream();
            var buf = new byte[1024];
            for (int len; (len = stream.read(buf)) != -1;)
                result.write(buf, 0, len);
            return result.toString(encoding);
        } catch (IOException ex) {
            throw new RuntimeException(ex);
        }
    }

    public static List<String> splitBySpaces(String input) {  // unless quoted
        var result = new ArrayList<String>();

        var pattern = Pattern.compile("[^\\s\"']+|\"([^\"]*)\"|'([^']*)'");
        var matcher = pattern.matcher(input);

        while (matcher.find()) {
            if (matcher.group(1) != null) {
                result.add(matcher.group(1));
            } else if (matcher.group(2) != null) {
                result.add(matcher.group(2));
            } else {
                result.add(matcher.group());
            }
        }

        return result;
    }

    public static String strip(String str, String toStrip) {
        return stripTrailing(stripLeading(str, toStrip), toStrip);
    }

    public static String stripTrailing(String str, String toStrip) {
        while (str.endsWith(toStrip))
            str = str.substring(0, str.length() - toStrip.length());
        return str;
    }

    public static String stripLeading(String str, String toStrip) {
        while(str.startsWith(toStrip))
            str = str.substring(toStrip.length());
        return str;
    }

    public static Supplier<String> counter(String prefix) {
        var i = new AtomicInteger();
        return () -> prefix + "_" + i.getAndIncrement();
    }

    public static Supplier<String> uniqueCounter() {
        return uniqueCounter("");
    }

    public static Supplier<String> uniqueCounter(String prefix) {
        return counter(prefix + timeCode(LocalDateTime.now(), 5));
    }

    public static String replaceVariables(String maybeVars, Function<String, String> lookup)
    {
        var matcher = varPattern.matcher(maybeVars);
        while (matcher.find()) {
            var variable = matcher.group();
            maybeVars = maybeVars.replace(variable, lookup.apply(variable.substring(2, variable.length()-1)));
        }
        return maybeVars;
    }

    public static String[] splitWithQuotes(String args) {
        var sc = new Scanner(args);
        var pattern = Pattern.compile("\"[^\"]*\"|'[^']*'|[^ \"]+");

        var result = new ArrayList<String>();
        String token;
        while ((token = sc.findInLine(pattern)) != null) {
            if (token.startsWith("\""))
                token = token.substring(1, token.length() - 1);
            result.add(token);
        }
        return result.toArray(new String[0]);
    }

    public static String nullToEmpty(Object str) {
        return str == null ? "" : str.toString();
    }

    public static String[] rsplit(String str, String sep) {
        return rsplit(str, Pattern.quote(sep), 2);
    }

    public static String[] rsplit(String str, String sep, int limit) {
        var parts = str.split(sep);
        if (parts.length <= limit)
            return parts;

        var result = new String[limit];
        var joinCount = parts.length - limit + 1;
        var sb = new StringBuilder();
        for (var i = 0; i < joinCount; i++) {
            if (i > 0)
                sb.append(sep);
            sb.append(parts[i]);
        }
        result[0] = sb.toString();
        System.arraycopy(parts, joinCount, result, 1, limit - 1);
        return result;
    }

    public static String stripDigitSuffix(String str) {
        var last = str.length() - 1;
        var i = last;
        while (i >= 0 && Character.isDigit(str.charAt(i)))
            --i;

        return i == last ? str : str.substring(0, i+1);
    }

    @SuppressWarnings("unchecked")
    public static <T> T parse(String str, Class<T> cls) {
        if (cls == String.class)
            return (T)str;
        if (cls == Integer.class)
            return (T)(Integer)Integer.parseInt(str.replace("_", ""));
        if (cls == Long.class)
            return (T)(Long)Long.parseLong(str.replace("_", ""));
        if (cls == Double.class)
            return (T)(Double)Double.parseDouble(str.replace("_", ""));
        if (cls == Boolean.class)
            return (T)(Boolean)Boolean.parseBoolean(str);
        if (cls == List.class)
            return (T)List.of(str.split(","));
        if (cls == Set.class)
            return (T)Set.of(str.split(","));
        if (cls == Duration.class)
            return (T)Dttms.parseDuration(str);
        throw new RuntimeException("Unsupported type: " + cls);
    }
}
