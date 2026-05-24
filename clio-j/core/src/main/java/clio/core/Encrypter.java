package clio.core;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Arrays;

public class Encrypter {
    private final String secret;
    private final SecureRandom random;

    public Encrypter(String secret) {
        this.secret = secret;
        this.random = new SecureRandom();
    }

    public String hash(String user, String password) {
        var salt = new byte[16];
        random.nextBytes(salt);
        var dk = pbkdf2((password + user + secret).toCharArray(), salt);
        var hash = new byte[salt.length + dk.length];
        System.arraycopy(salt, 0, hash, 0, salt.length);
        System.arraycopy(dk, 0, hash, salt.length, dk.length);
        var enc = Base64.getUrlEncoder().withoutPadding();
        return enc.encodeToString(hash);
    }

    public boolean authenticate(String user, String password, String hash) {
        var dhash = Base64.getUrlDecoder().decode(hash);
        var salt = Arrays.copyOfRange(dhash, 0, 16);
        var check = pbkdf2((password + user + secret).toCharArray(), salt);
        var zero = 0;
        for (var i = 0; i < check.length; i++)
            zero |= dhash[salt.length + i] ^ check[i];
        return zero == 0;
    }

    private static byte[] pbkdf2(char[] password, byte[] salt) {
        try {
            var spec = new PBEKeySpec(password, salt, 1 << 16, 128);
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1").generateSecret(spec).getEncoded();
        } catch (Exception ex) {
            throw new RuntimeException(ex);
        }
    }
}
