import asyncio
import logging

import typer

from app.clients.ziti import ZitiClient
from app.conf import Settings


BATCH_SIZE = 100
ZROK_PROXY_CONFIG = "zrok.proxy.v1"

logger = logging.getLogger(__name__)


async def bootstrap(settings: Settings, skip_frontend: bool = False):
    """
    func Bootstrap(skipFrontend bool, inCfg *config.Config) error {
        cfg = inCfg

        if v, err := store.Open(cfg.Store); err == nil {
            str = v
        } else {
            return errors.Wrap(err, "error opening store")
        }

        logrus.Info("connecting to the ziti edge management api")
        edge, err := zrokEdgeSdk.Client(cfg.Ziti)
        if err != nil {
            return errors.Wrap(err, "error connecting to the ziti edge management api")
        }

        env, err := environment.LoadRoot()
        if err != nil {
            return err
        }

        var frontendZId string
        if !skipFrontend {
            logrus.Info("creating identity for public frontend access")

            if frontendZId, err = getIdentityId(env.PublicIdentityName()); err == nil {
                logrus.Infof("frontend identity: %v", frontendZId)
            } else {
                frontendZId, err = bootstrapIdentity(env.PublicIdentityName(), edge)
                if err != nil {
                    panic(err)
                }
            }
            if err := assertIdentity(frontendZId, edge); err != nil {
                panic(err)
            }
            if err := assertErpForIdentity(env.PublicIdentityName(), frontendZId, edge); err != nil {
                panic(err)
            }

            tx, err := str.Begin()
            if err != nil {
                panic(err)
            }
            defer func() { _ = tx.Rollback() }()
            publicFe, err := str.FindFrontendWithZId(frontendZId, tx)
            if err != nil {
                logrus.Warnf("missing public frontend for ziti id '%v'; please use 'zrok admin create frontend %v public https://{token}.your.dns.name' to create a frontend instance", frontendZId, frontendZId)
            } else {
                if publicFe.PublicName != nil && publicFe.UrlTemplate != nil {
                    logrus.Infof("found public frontend entry '%v' (%v) for ziti identity '%v'", *publicFe.PublicName, publicFe.Token, frontendZId)
                } else {
                    logrus.Warnf("found frontend entry for ziti identity '%v'; missing either public name or url template", frontendZId)
                }
            }
        }

        if err := assertZrokProxyConfigType(edge); err != nil {
            return err
        }

        return nil
    }
    """
    print("Bootstrapping...")
    print(f"settings={settings}, skip_frontend={skip_frontend}")


async def assert_zrok_proxy_config_type(ziti_client: ZitiClient) -> None:
    try:
        filter_exp = f"name=\"{ZROK_PROXY_CONFIG}\""
        config_types = ziti_client.list_config_types(filter_exp)
    except Exception as e:
        logging.error(f"Error listing config types: {e}")
        raise RuntimeError(f"Error listing config types")

    config_types_count = 0
    async for _ in config_types:
        config_types_count += 1

    if config_types_count < 1:
        try:
            config_type = await ziti_client.create_config_type(name=ZROK_PROXY_CONFIG)
            logging.info(f"Created '{ZROK_PROXY_CONFIG}' config type with id '{config_type['id']}'")
        except Exception as e:
            logging.error(f"Error creating '{ZROK_PROXY_CONFIG}' config type: {e}")
            raise RuntimeError(f"Error creating '{ZROK_PROXY_CONFIG}' config type")
    elif config_types_count > 1:
        logging.error(
            f"Found {config_types_count} '{ZROK_PROXY_CONFIG}' config types; expected 0 or 1"
        )
        raise RuntimeError(
            f"Found {config_types_count} '{ZROK_PROXY_CONFIG}' config types; expected 0 or 1"
        )
    else:
        logging.info(f"Found '{ZROK_PROXY_CONFIG}' config type with id '{ZROK_PROXY_CONFIG}'")


async def assert_identity(z_id: str, ziti_client: ZitiClient) -> None:
    try:
        filter_exp = f"id=\"{z_id}\""
        identities = ziti_client.list_edge_router_policies(filter_exp)
    except Exception as e:
        logging.error(f"Error listing edge identities for '{z_id}': {e}")
        raise RuntimeError(f"Error listing edge identities for '{z_id}'")

    identities_count = 0
    async for _ in identities:
        identities_count += 1

    if identities_count != 1:
        logging.error(f"Found {identities} identities for '{z_id}'")

    logging.info(f"Asserted identity '{z_id}'")


async def bootstrap_identity(name: str, ziti_client: ZitiClient) -> str:
    """
    func bootstrapIdentity(name string, edge *rest_management_api_client.ZitiEdgeManagement) (string, error) {


        idc, err := zrokEdgeSdk.CreateIdentity(name, restModelEdge.IdentityTypeDevice, nil, edge)
        if err != nil {
            return "", errors.Wrapf(rest_util.WrapErr(err), "error creating '%v' identity", name)
        }

        zId := idc.Payload.Data.ID
        cfg, err := zrokEdgeSdk.EnrollIdentity(zId, edge)
        if err != nil {
            return "", errors.Wrapf(rest_util.WrapErr(err), "error enrolling '%v' identity", name)
        }

        var out bytes.Buffer
        enc := json.NewEncoder(&out)
        enc.SetEscapeHTML(false)
        err = enc.Encode(&cfg)
        if err != nil {
            return "", errors.Wrapf(err, "error encoding identity config '%v'", name)
        }
        if err := env.SaveZitiIdentityNamed(name, out.String()); err != nil {
            return "", errors.Wrapf(err, "error saving identity config '%v'", name)
        }
        return zId, nil
    }
    """
    return ""


async def assert_erp_for_identity(name: str, z_id: str, ziti_client: ZitiClient) -> None:
    """
    Ensure that an Edge Router Policy exists for the given identity.
    If not, create one.
    """

    try:
        filter_exp = f"name='{name}' and tags.zrok != null"
        policies = ziti_client.list_edge_router_policies(filter_exp)
    except Exception as e:
        logging.error(f"Error listing edge router policies for '{name}' ({z_id}): {e}")
        raise RuntimeError(f"Error listing edge router policies for '{name}' ({z_id})")

    policies_count = 0
    async for _ in policies:
        policies_count += 1

    if policies_count != 1:
        logging.info(f"Creating ERP for '{name}' ({z_id})")
        try:
            policy = await ziti_client.create_edge_router_policy(name, z_id)
            logging.info(f"Created edge router policy '{policy['id']}' for ziti identity '{z_id}'")
        except Exception as e:
            logging.error(f"Error creating ERP for '{name}' ({z_id}): {e}")
            raise RuntimeError(f"Error creating ERP for '{name}' ({z_id})")

    logging.info(f"Asserted ERPs for '{name}' ({z_id})")


def command(
    ctx: typer.Context,
    skip_frontend: bool = typer.Option(
        False,
        "--skip-frontend",
        help="Skip frontend identity bootstrapping",
    ),
):
    asyncio.run(bootstrap(ctx.obj, skip_frontend))
