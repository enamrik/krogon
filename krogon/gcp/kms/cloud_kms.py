from krogon.logger import Logger
from krogon.gcp.on_http404 import on_http404
from base64 import b64encode
import krogon.gcp.gcloud as gc
import krogon.either as E
import krogon.maybe as M


def new_cloud_kms(gcloud: gc.GCloud, logger: Logger):
    return gc.create_api(gcloud, name='cloudkms', version='v1') \
           | E.then | (lambda client: CloudKMS(client, logger))


class CloudKMS:
    def __init__(self, client, logger: Logger):
        self.client = client
        self.logger = logger

        self.get_keyring = lambda **kwargs: \
            E.try_catch(lambda: client.projects().locations().keyRings().get(**kwargs).execute()) \
            | E.then | (lambda r: M.Just(r)) \
            | E.catch_error | on_http404(return_result=E.Success(M.Nothing()))

        self.create_keyring = lambda **kwargs: \
            E.try_catch(lambda: client.projects().locations().keyRings().create(**kwargs).execute())

        self.get_key = lambda **kwargs: \
            E.try_catch(lambda: client.projects().locations().keyRings().cryptoKeys().get(**kwargs).execute()) \
            | E.then | (lambda r: M.Just(r)) \
            | E.catch_error | on_http404(return_result=E.Success(M.Nothing()))

        self.create_key = lambda **kwargs: \
            E.try_catch(lambda: client.projects().locations().keyRings().cryptoKeys().create(**kwargs).execute())

        self.encrypt_key = lambda **kwargs: \
            E.try_catch(lambda: client.projects().locations().keyRings().cryptoKeys().encrypt(**kwargs).execute())


def encrypt(ck: CloudKMS, key: str, value: str, project_id, region):
    keyring_name = '{}-keyring'.format(key)
    keyring_path = 'projects/{}/locations/{}'.format(project_id, region)
    keyring_full_name = '{}/keyRings/{}'.format(keyring_path, keyring_name)
    key_full_name = '{}/cryptoKeys/{}'.format(keyring_full_name, key)

    return _apply_keyring(ck, keyring_name, keyring_full_name, keyring_path) \
        | E.then | (lambda _: _apply_key(ck, key, key_full_name, keyring_full_name)) \
        | E.then | (lambda _: _encrypt_with_key(ck, key_full_name, value))


def _encrypt_with_key(ck: CloudKMS, key_full_name: str, value: str):
    ck.logger.info('KMS: Encrypting key: {}'.format(key_full_name))

    return ck.encrypt_key(name=key_full_name,
                          body={'plaintext': b64encode(value.encode('utf-8')).decode('utf-8')}) \
           | E.then | (lambda r: dict(ciphertext=r['ciphertext'],
                                      key_full_name=key_full_name))


def _apply_key(ck: CloudKMS, key: str, key_full_name: str, keyring_full_name: str):
    return ck.get_key(name=key_full_name) \
           | E.then | (lambda maybe_resp:
                       maybe_resp
                       | M.from_maybe | dict(
                           if_just=lambda resp: resp,
                           if_nothing=lambda: ck.create_key(
                               parent=keyring_full_name,
                               cryptoKeyId=key,
                               body={'purpose': 'ENCRYPT_DECRYPT'}))
                       )


def _apply_keyring(ck: CloudKMS, keyring_name: str, keyring_full_name: str, keyring_path: str):
    return ck.get_keyring(name=keyring_full_name) \
           | E.then | (lambda maybe_resp:
                       maybe_resp
                       | M.from_maybe | dict(
                           if_just=lambda resp: resp,
                           if_nothing=lambda: ck.create_keyring(
                               parent=keyring_path,
                               keyRingId=keyring_name,
                               body={'name': keyring_full_name}))
                       )

