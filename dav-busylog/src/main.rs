const URL: &str = "https://www.boulderado.de/boulderadoweb/gym-clientcounter/index.php?mode=get&token=eyJhbGciOiJIUzI1NiIsICJ0eXAiOiJKV1QifQ.eyJjdXN0b21lciI6IkRBVkVybGFuZ2VuMjMyMDIwIn0.Fr3KR0obdp_aYzCIclQTMZr0dVIxT0bfyUVODU_u64M";

fn parse_busy_value_from_html(html: &str) -> Result<usize, Box<dyn std::error::Error>> {
    let dom = scraper::Html::parse_document(&html);

    let selector = scraper::Selector::parse(".actcounter-content > span").unwrap();
    let value_str = dom
        .select(&selector)
        .next()
        .ok_or("Could not extract counter value from HTML")?
        .inner_html();

    let value_num = value_str.parse::<usize>()?;

    Ok(value_num)
}

fn fetch_busy_value_from_remote(url: &str) -> Result<usize, Box<dyn std::error::Error>> {
    let html = reqwest::blocking::get(url)?.text()?;
    let busy_value = parse_busy_value_from_html(&html)?;
    Ok(busy_value)
}

fn main() {
    loop {
        match fetch_busy_value_from_remote(URL) {
            Ok(value) => {
                println!("Current: {:#?}", value)
            }
            Err(error) => {
                println!("Failed: {}", error)
            }
        };

        std::thread::sleep(std::time::Duration::from_millis(1000));
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn extract_value_from_valid_html() {
        let valid_html = r#"
				<!DOCTYPE html>
				<html lang="de">
				  <head>
				    <meta charset="utf-8" />
				    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1" />
					<meta http-equiv="X-UA-Compatible" content="IE=edge">
				    <link rel="stylesheet" type="text/css" href="css/public.css"><link rel="stylesheet" href="/fonts/asap.css" as="style">
				    <title>Boulderado Counter</title>    
				  </head>
				  <body>
					<div data-value="26" id="visitorcount-container" class="freepercent2 ">						
				<div data-value="26" class="actcounter zoom"><div class="actcounter-title"><span>Besucher</span></div><div class="actcounter-content"><span data-value="26">26</span></div></div><div data-value="4" class="freecounter zoom"><div class="freecounter-title"><span>Frei</span></div><div class="freecounter-content"><span data-value="4">4</span></div></div>						
					</div>
				  </body>
				</html>
"#;

        let value = parse_busy_value_from_html(&valid_html).unwrap();
        assert_eq!(value, 26);
    }

    #[test]
    fn fail_to_find_value_in_invalid_html() {
        let html_without_value = r#"
				<!DOCTYPE html>
				<html lang="de">
				  <head>
				    <meta charset="utf-8" />
				    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1" />
					<meta http-equiv="X-UA-Compatible" content="IE=edge">
				    <link rel="stylesheet" type="text/css" href="css/public.css"><link rel="stylesheet" href="/fonts/asap.css" as="style">
				    <title>Boulderado Counter</title>    
				  </head>
				  <body>
					<div data-value="26" id="visitorcount-container" class="freepercent2 ">						
				  </body>
				</html>
"#;

        let result = parse_busy_value_from_html(&html_without_value);
        let error = result.unwrap_err();
        assert_eq!(
            error.to_string(),
            "Could not extract counter value from HTML"
        );
    }

    #[test]
    fn fail_to_parse_value_as_number() {
        let html_with_unparseable_value = r#"
				<!DOCTYPE html>
				<html lang="de">
				  <head>
				    <meta charset="utf-8" />
				    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1" />
					<meta http-equiv="X-UA-Compatible" content="IE=edge">
				    <link rel="stylesheet" type="text/css" href="css/public.css"><link rel="stylesheet" href="/fonts/asap.css" as="style">
				    <title>Boulderado Counter</title>    
				  </head>
				  <body>
					<div data-value="26" id="visitorcount-container" class="freepercent2 ">						
				<div data-value="26" class="actcounter zoom"><div class="actcounter-title"><span>Besucher</span></div><div class="actcounter-content"><span data-value="26">twentysix</span></div></div><div data-value="4" class="freecounter zoom"><div class="freecounter-title"><span>Frei</span></div><div class="freecounter-content"><span data-value="4">4</span></div></div>						
					</div>
				  </body>
				</html>
"#;

        let result = parse_busy_value_from_html(&html_with_unparseable_value);
        let error = result.unwrap_err();
        assert_eq!(error.to_string(), "invalid digit found in string");
    }
}
