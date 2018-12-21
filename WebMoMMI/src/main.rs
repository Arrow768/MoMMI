#![feature(proc_macro_hygiene, decl_macro)]

#[macro_use]
extern crate rocket;
#[macro_use]
extern crate serde_derive;

mod mommi;
mod github;
mod config;

use crate::config::MoMMIConfig;

#[get("/twohundred")]
fn twohundred() -> &'static str {
    "hi BYOND!"
}

fn main() {
    let mut rocket = rocket::ignite().mount(
        "/",
        routes![
            twohundred,
            github::post_github,
            github::post_github_new,
            github::post_github_new_specific,
            github::post_github_alt,
        ],
    );
    let config = match MoMMIConfig::new(rocket.config()) {
        Ok(x) => x,
        Err(x) => {
            println!("Failed to launch, broken config: {}", x);
            return
        }
    };

    if config.has_commloop() {
        rocket = rocket.mount(
            "/",
            routes![
                mommi::get_nudgeold,
                mommi::get_nudge,
                mommi::get_nudge_new,
            ]
        )
    }

    rocket.manage(config).launch();
}
