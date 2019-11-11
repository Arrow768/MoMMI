//! Interfacing with MoMMIv2.

use crate::config::MoMMIConfig;
use byteorder::{NetworkEndian, ReadBytesExt, WriteBytesExt};
use crypto::hmac::Hmac;
use crypto::mac::Mac;
use crypto::sha2::Sha512;
use rocket::request::Form;
use rocket::response::status::Accepted;
use rocket::State;
use rocket_contrib::json::Json;
use serde::Serialize;
use serde_json::json;
use std::io::{Error as IoError, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::sync::Arc;

/// Sends a message to the MoMMI commloop.
/// Really can't get simpler than this.
pub fn commloop<A: ToSocketAddrs, S: Serialize>(
    address: A,
    password: &str,
    message_type: &str,
    meta: &str,
    content: S,
) -> Result<(), MoMMIError> {
    let json = json!({
        "type": message_type,
        "meta": meta,
        "cont": content
    })
    .to_string();

    let mut hmac = Hmac::new(Sha512::new(), password.as_bytes());
    hmac.input(json.as_bytes());
    let result = hmac.result();

    let mut socket = TcpStream::connect(address)?;
    socket.write_all(b"\x30\x05")?;
    socket.write_all(result.code())?;
    socket.write_u32::<NetworkEndian>(json.as_bytes().len() as u32)?;
    socket.write_all(json.as_bytes())?;
    socket.flush()?;

    let code = socket.read_u8()?;

    match code {
        0 => Ok(()),
        x => Err(MoMMIError::from(x)),
    }
}

#[derive(Debug)]
pub enum MoMMIError {
    IdBytes,
    Json,
    Auth,
    Unknown,
    Io(IoError),
}

impl From<u8> for MoMMIError {
    fn from(code: u8) -> MoMMIError {
        match code {
            1 => MoMMIError::IdBytes,
            2 => MoMMIError::Json,
            3 => MoMMIError::Auth,
            _ => MoMMIError::Unknown,
        }
    }
}

impl From<IoError> for MoMMIError {
    fn from(error: IoError) -> MoMMIError {
        MoMMIError::Io(error)
    }
}

// Damnit past me for forcing current me to do this so future me has to clean it up sometime!

#[derive(Clone, Debug, FromForm)]
pub struct NudgeOld {
    admin: Option<bool>,
    pass: String,
    content: String,
    ping: Option<bool>,
}

#[derive(Clone, Debug, FromForm, Deserialize)]
pub struct Nudge {
    meta: String,
    pass: String,
    content: String,
    ping: Option<bool>,
}

#[derive(Clone, Debug, FromForm, Deserialize)]
pub struct PostNudgeData {
    pass: String,
    content: String,
    ping: Option<bool>
}

// Kill this monstrosity.
// NOW.
impl From<NudgeOld> for Nudge {
    fn from(old: NudgeOld) -> Nudge {
        Nudge {
            meta: match old.admin {
                Some(true) => "adminhelp".into(),
                _ => "server_status".into(),
            },
            pass: old.pass,
            content: old.content,
            ping: old.ping,
        }
    }
}

// GET because >BYOND
#[get("/discord?<nudge..>")]
pub fn get_nudgeold(
    nudge: Form<NudgeOld>,
    config: State<Arc<MoMMIConfig>>,
) -> Result<Accepted<&'static str>, MoMMIError> {
    nudge_internal(&nudge.into_inner().into(), config)
}

#[get("/discord?<nudge..>", rank = 2)]
pub fn get_nudge(
    nudge: Form<Nudge>,
    config: State<Arc<MoMMIConfig>>,
) -> Result<Accepted<&'static str>, MoMMIError> {
    nudge_internal(&nudge, config)
}

#[get("/mommi/nudge?<nudge..>")]
pub fn get_nudge_new(
    nudge: Form<Nudge>,
    config: State<Arc<MoMMIConfig>>,
) -> Result<Accepted<&'static str>, MoMMIError> {
    nudge_internal(&nudge, config)
}

#[post("/mommi/nudge/<meta>", data="<nudge>")]
pub fn post_nudge(
    meta: String,
    nudge: Json<PostNudgeData>,
    config: State<Arc<MoMMIConfig>>,
) -> Result<Accepted<&'static str>, MoMMIError> {
    let data = Nudge {
        meta,
        pass: nudge.pass.clone(),
        ping: nudge.ping,
        content: nudge.content.clone()
    };

    nudge_internal(&data, config)
}


fn nudge_internal(
    nudge: &Nudge,
    config: State<Arc<MoMMIConfig>>,
) -> Result<Accepted<&'static str>, MoMMIError> {
    // This route does not get mounted when there's no commloop.
    let (addr, pass) = config
        .get_commloop()
        .expect("Nudge route requested without commloop config.");

    let message = json!({
        "pass": nudge.pass.clone(),
        "content": nudge.content.clone(),
        "ping": nudge.ping.unwrap_or(false),
    });

    commloop(addr, pass, "gamenudge", &nudge.meta, &message)?;
    Ok(Accepted(Some("MoMMI successfully received the message.")))
}

#[post("/mommi/ss14/<id>", format="json", data="<message>")]
pub fn post_ss14(
    id: String,
    message: Json<serde_json::Value>,
    config: State<Arc<MoMMIConfig>>,
) -> Result<Accepted<&'static str>, MoMMIError> {
    let (addr, pass) = config
        .get_commloop()
        .expect("SS14 route requested without commloop config.");

    commloop(addr, pass, "ss14", &id, message.into_inner())?;
    Ok(Accepted(Some("MoMMI successfully received the message.")))
}
