package clio.core;

public class Numbers {
    public static long longPow(long a, long b) {
        long r = 1;
        for (long i = 0; i < b; i++)
            r *= a;
        return r;
    }

    public static int sign(long v) {
        if (v == 0)
            return 0;
        if (v > 0)
            return 1;
        return -1;
    }

    public static boolean sameSign(long a, long b) {
        return sign(a) == sign(b);
    }

    public static long least(long a, long b) {
        // return closed to zero regardless of sign
        if (Math.abs(a) > Math.abs(b))
            return b;
        else
            return a;
    }

    public static double deviation(double a, double b) {
        if (a == 0.0 || b == 0.0)
            return 1.0;

        if (Math.abs(a) > Math.abs(b))
            return Math.abs((a-b)/a);
        else
            return Math.abs((a-b)/b);
    }

    public static long floorToZero(double x) {
        return floorToZero(x, 1.0);
    }

    public static long floorToZero(double x, double step) {
        if (x < 0)
            return -1 * floorToZero(-x, step);

        return Math.round(Math.floor(x / step) * step);
    }

    public static double clip(double x, double min, double max) {
        return Math.min(Math.max(x, min), max);
    }

    public static <T extends Comparable<X>, X> T min(T a, T b) { return a.compareTo((X)b) < 0 ? a : b; }

    public static double round(double x, int dp) {
        var scale = Math.pow(10, dp);
        return Math.round(x * scale) / scale;
    }

    public static double asDouble(Object o) {
        return switch (o) {
            case null -> Double.NaN;
            case Integer i -> i.doubleValue();
            case Long l -> l.doubleValue();
            case Float v -> v.doubleValue();
            default -> (Double) o;
        };

    }
}
