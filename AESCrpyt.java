import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.Console;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.nio.ByteBuffer;
import java.security.InvalidAlgorithmParameterException;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.CipherInputStream;
import javax.crypto.CipherOutputStream;
import javax.crypto.NoSuchPaddingException;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import javax.xml.bind.DatatypeConverter;

public class AESCrpyt {

	private static final int HEAD_LEN = 16;

	private static String TYPE = "AES";

	private static int KeySizeAES128 = 16;

	private static int BUFFER_SIZE = 1024 * 16;

	private static int _MAGIC_NUM = 0xecececec;
	private static long _VERSION = 2;

	private static void derive_key_and_iv(byte[] password, byte[] salt, int key_length, int iv_length, byte[] key,
			byte[] iv) {
		ByteBuffer d = ByteBuffer.allocate(key_length + iv_length);
		byte[] d_i = new byte[0];
		try {

			while (d.position() < key_length + iv_length) {
				MessageDigest messageDigest = MessageDigest.getInstance("MD5");

				byte[] data = new byte[d_i.length + password.length + salt.length];
				System.arraycopy(d_i, 0, data, 0, d_i.length);
				System.arraycopy(password, 0, data, d_i.length, password.length);
				System.arraycopy(salt, 0, data, d_i.length + password.length, salt.length);

				messageDigest.update(data);
				byte[] dataMd5 = messageDigest.digest();
				d_i = dataMd5;

				d.put(d_i);
			}

			byte[] result = d.array();
			System.arraycopy(result, 0, key, 0, key_length);
			System.arraycopy(result, key_length, iv, 0, iv_length);
		} catch (NoSuchAlgorithmException e) {
		}
	}

	private static Cipher getCipher(int mode, String password, byte[] salt) {

		// mode =Cipher.DECRYPT_MODE or Cipher.ENCRYPT_MODE
		byte[] key = new byte[KeySizeAES128];
		byte[] iv = new byte[KeySizeAES128];

		derive_key_and_iv(password.getBytes(), salt, KeySizeAES128, KeySizeAES128, key, iv);

		return getCipher(mode, key, iv);
	}

	private static Cipher getCipher(int mode, byte[] key, byte[] iv) {

		// mode =Cipher.DECRYPT_MODE or Cipher.ENCRYPT_MODE

		Cipher mCipher;

		IvParameterSpec ivParam = new IvParameterSpec(iv);

		try {

			mCipher = Cipher.getInstance(TYPE + "/CBC/PKCS5Padding");

			SecretKeySpec keySpec = new SecretKeySpec(key, TYPE);

			mCipher.init(mode, keySpec, ivParam);

			return mCipher;

		}

		catch (InvalidKeyException e) {

			e.printStackTrace();

		}

		catch (NoSuchAlgorithmException e) {

			e.printStackTrace();

		}

		catch (NoSuchPaddingException e) {

			e.printStackTrace();

		}

		catch (InvalidAlgorithmParameterException e) {

			// TODO Auto-generated catch block

			e.printStackTrace();

		}

		return null;

	}

	public static void encrypt(String srcFile, String destFile, String privateKey) {

		try {
			encrypt(new FileInputStream(srcFile), new FileOutputStream(destFile), privateKey);

		} catch (FileNotFoundException e) {

			e.printStackTrace();

		}

	}

	public static void decrypt(String srcFile, String destFile, String privateKey) {

		try {
			decrypt(new FileInputStream(srcFile), new FileOutputStream(destFile), privateKey);

		} catch (FileNotFoundException e) {

			e.printStackTrace();

		}

	}

	public static void decrypt(InputStream in, OutputStream out, String password) {

		byte[] readBuffer = new byte[BUFFER_SIZE];

		CipherInputStream fis = null;
		BufferedInputStream bis = null;
		BufferedOutputStream fos = null;

		int size;

		try {

			bis = new BufferedInputStream(in);
			
			// Read head info
			byte[] head_info = new byte[HEAD_LEN];
			byte[] salt = null;
			bis.read(head_info);

			// Parse head info
			int magic = bytes2int(head_info);
			int version = head_info[4];

            if (magic == _MAGIC_NUM) {
                salt = new byte[KeySizeAES128];
                bis.read(salt);
            }
            else {
                salt = head_info;
            }

			int key_len = bis.read();
			
			System.out.println("version: " + version);
			System.out.println("key_len: " + key_len);
			
			byte[] key = new byte[key_len];
			byte[] iv = new byte[KeySizeAES128];
			derive_key_and_iv(password.getBytes(), salt, key_len, KeySizeAES128, key, iv);

			Cipher deCipher = getCipher(Cipher.DECRYPT_MODE, key, iv);
			
			if (deCipher != null) {

				fis = new CipherInputStream(bis, deCipher);
				fos = new BufferedOutputStream(

						out);

				while ((size = fis.read(readBuffer, 0, BUFFER_SIZE)) >= 0) {

					fos.write(readBuffer, 0, size);

				}

				fos.flush();
			}
			else {

				System.out.print("The file format is not supported. magic: " + magic + " version: " + version);
			}

		} catch (FileNotFoundException e) {

			e.printStackTrace();

		} catch (IOException e) {

			e.printStackTrace();

		} finally {

			if (fis != null) {

				try {
					fis.close();
				} catch (IOException e) {
				}

			}

			if (fos != null) {

				try {
					fos.flush();
				} catch (IOException e) {
				}

				try {
					fos.close();
				} catch (IOException e) {
				}

			}

		}

	}

	private static int bytes2int(byte[] head_info) {
		ByteBuffer buffer = ByteBuffer.allocate(4);
	    buffer.put(head_info, 0, buffer.limit());
	    buffer.flip();//need flip 
	    return buffer.getInt();
	}

	public static void encrypt(InputStream in, OutputStream out, String privateKey) {

		byte[] readBuffer = new byte[BUFFER_SIZE];
		SecureRandom random = new SecureRandom();
		byte[] salt = new byte[KeySizeAES128];
		random.nextBytes(salt);
		Cipher enCipher = getCipher(Cipher.ENCRYPT_MODE, privateKey, salt);

		if (enCipher == null)
			return; // init failed.

		CipherOutputStream fos = null;
		BufferedOutputStream bos = null;
		BufferedInputStream fis = null;

		int size;

		try {
			bos = new BufferedOutputStream(out);
			
			// Write head info
			ByteBuffer head_info = ByteBuffer.allocate(HEAD_LEN);
			head_info.clear();
			head_info.putInt(_MAGIC_NUM);
			head_info.put((byte) _VERSION);
			bos.write(head_info.array());
			
			// Write salt, key_len
			bos.write(salt);
			bos.write((byte)KeySizeAES128);

			fos = new CipherOutputStream(bos, enCipher);

			fis = new BufferedInputStream(in);

			while ((size = fis.read(readBuffer, 0, BUFFER_SIZE)) >= 0) {
				fos.write(readBuffer, 0, size);
			}

			fos.flush();

		} catch (FileNotFoundException e) {

			e.printStackTrace();

		} catch (IOException e) {

			e.printStackTrace();

		} finally {

			if (fis != null) {

				try {
					fis.close();
				} catch (IOException e) {
				}

			}

			if (fos != null) {

				try {
					fos.flush();
				} catch (IOException e) {
				}

				try {
					fos.close();
				} catch (IOException e) {
				}

			}

		}
	}

	public static void main(String[] args) {

		boolean decryptMode = false;
		boolean stringMode = false;
		String pathInput = null;
		String pathOutput = null;

		for (String arg : args) {
			if (arg.equals("-d")) {
				decryptMode = true;
			} else if (arg.equals("-s")) {
				stringMode = true;
			} else if (pathInput == null) {
				pathInput = arg;
			} else {
				pathOutput = arg;
			}
		}

		String password = ReadValidPassword(!decryptMode);
		System.out.println(password);
		
		if (!stringMode && (pathInput == null || pathOutput == null)) {
			System.exit(0);
		}
		
		if (stringMode) {
			if (pathInput == null) {
				System.exit(0);
			}
			try {
				ByteArrayOutputStream out = new ByteArrayOutputStream();
				
				if (decryptMode) {
					byte[] data = DatatypeConverter.parseBase64Binary(pathInput);
					InputStream in = new ByteArrayInputStream(data);
					AESCrpyt.decrypt(in, out,
							password);
					System.out.println(out.toString());
				} else {
					InputStream in = new ByteArrayInputStream(pathInput.getBytes("UTF-8"));
					AESCrpyt.encrypt(in, out, password);
					String result = DatatypeConverter.printBase64Binary(out.toByteArray());
					System.out.println(result);
				}
				
				out.flush();
			} catch (UnsupportedEncodingException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			System.exit(0);
		}

		if (decryptMode) {
			AESCrpyt.decrypt(pathInput, pathOutput,
					password);
		} else {
			AESCrpyt.encrypt(pathInput, pathOutput, password);
		}
	}

	private static String ReadValidPassword(boolean confirm) {
		String password1 = null;
		String password2 = null;
		while (password1 == null || password2 == null || password1.length() == 0 || !password1.equals(password2)) {
			password1 = null;
			password2 = null;

			Console console = System.console();
			if (console == null) {
			    System.out.println("Couldn't get Console instance");
			    System.exit(1);
			}

			char[] passwordArray = console.readPassword("Password: ");
			password1 = new String(passwordArray);
			if (confirm) {
				passwordArray = console.readPassword("Re-input Password: ");
				password2 = new String(passwordArray);
			}
			else {
				password2 = password1;
			}
		}
		return password1;
	}

}
