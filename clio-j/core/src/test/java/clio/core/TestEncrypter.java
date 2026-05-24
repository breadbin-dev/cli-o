package clio.core;

import clio.core.Encrypter;
import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class TestEncrypter {

    @Test
    public void testEncrypter() {
        var enc = new Encrypter("mysecret");
        var hash = enc.hash("a_user", "a_password");

        assertTrue(enc.authenticate("a_user", "a_password", hash));
        assertFalse(enc.authenticate("a_user", "a_typo", hash));
        assertFalse(enc.authenticate("b_user", "a_password", hash));

        enc = new Encrypter("mysecret");
        assertTrue(enc.authenticate("a_user", "a_password", hash));
        assertFalse(enc.authenticate("a_user", "a_typo", hash));
        assertFalse(enc.authenticate("b_user", "a_password", hash));

        enc = new Encrypter("not_mysecret");
        assertFalse(enc.authenticate("a_user", "a_password", hash));
        assertFalse(enc.authenticate("a_user", "a_typo", hash));
        assertFalse(enc.authenticate("b_user", "a_password", hash));
    }

}
