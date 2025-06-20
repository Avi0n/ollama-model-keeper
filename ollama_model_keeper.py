import asyncio
import ollama
from datetime import datetime
import time
import logging

# Logging configuration
LOG_LEVEL = "INFO"  # Options: "DEBUG", "INFO"
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configure httpx logger to suppress HTTP request logs at INFO level
logging.getLogger("httpx").setLevel(logging.DEBUG if LOG_LEVEL == "DEBUG" else logging.WARNING)

# Global variables
TARGET_MODEL = "ENTER_MODEL_HERE"
OLLAMA_URI = "http://localhost:11434"
CYCLE_INTERVAL = 5  # Seconds between cycles
MONITOR_INTERVAL = 60  # Seconds between monitor checks
client = ollama.Client(host=OLLAMA_URI)

async def check_loaded_models():
    """Check if any models are loaded using ollama.ps."""
    try:
        response = client.ps()
        logger.debug(f"API ps response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error checking loaded models: {e}")
        raise

async def load_model(model_name):
    """Load a model using an empty /api/generate call with keep_alive=-1."""
    try:
        response = client.generate(model=model_name, keep_alive=-1)
        logger.debug(f"Generate response for loading {model_name}: {response}")
        logger.info(f"Successfully loaded model: {model_name} with keep_alive=-1")
    except Exception as e:
        logger.error(f"Error loading model {model_name}: {e}")
        raise

async def wait_for_unload(expires_at):
    """Wait until the specified datetime."""
    if isinstance(expires_at, datetime):
        expires_at_timestamp = expires_at.timestamp()
    else:
        expires_at_timestamp = expires_at
    current_time = time.time()
    remaining_seconds = max(0, expires_at_timestamp - current_time)
    if remaining_seconds > 0:
        logger.info(f"Waiting for {remaining_seconds:.0f} seconds until model unloads...")
        await asyncio.sleep(remaining_seconds)

async def monitor_for_other_models(target_model):
    """Monitor every 1 minute to check if another model is loaded."""
    try:
        while True:
            response = await check_loaded_models()
            models = response.get("models", [])
            logger.debug(f"Monitor check: {models}")
            model_names = [model["name"] for model in models]

            if target_model in model_names:
                if len(model_names) > 1:
                    other_models = [name for name in model_names if name != target_model]
                    logger.info(f"Other models detected: {other_models}")
                    return True
                logger.info(f"Only {target_model} is loaded. Checking again in 1 minute...")
                await asyncio.sleep(MONITOR_INTERVAL)
            else:
                # Target model is not loaded, check for other models
                if models:
                    latest_expires_at = 0
                    for model in models:
                        expires_at = model.get("expires_at", 0)
                        if expires_at == 0:  # Non-expiring model
                            logger.debug(f"Model {model['name']} has no expiration")
                            continue
                            
                        expires_at_timestamp = expires_at.timestamp() if isinstance(expires_at, datetime) else expires_at
                        logger.debug(f"Model {model['name']} expires at {datetime.fromtimestamp(expires_at_timestamp)}")
                        if expires_at_timestamp > time.time():
                            # 5 sec buffer to allow previous model to stop and unload
                            latest_expires_at = max(latest_expires_at, expires_at_timestamp) + 5

                    if latest_expires_at > 0:
                        logger.info(f"Other models loaded. Waiting for latest expires_at: {datetime.fromtimestamp(latest_expires_at)}")
                        await wait_for_unload(latest_expires_at)
                    else:
                        logger.info("Other models loaded with no expiration. Waiting 1 minute...")
                        await asyncio.sleep(MONITOR_INTERVAL)
                    continue  # Recheck after waiting
                else:
                    logger.info(f"{target_model} is no longer loaded and no other models are loaded.")
                    return False  # No models loaded, ready to reload target

    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        raise

async def main():
    """Main logic to check and load models, running indefinitely."""
    logger.info(f"Starting OllamaLoader at {datetime.now()}...")
    while True:
        try:
            logger.info(f"Entering main cycle at {datetime.now()}...")
            # Check if any models are loaded
            response = await check_loaded_models()
            logger.debug(f"Current models: {response.get('models', [])}")
            model_names = [model["name"] for model in response.get("models", [])]

            if TARGET_MODEL in model_names:
                # Target model is loaded, monitor for others
                logger.info(f"{TARGET_MODEL} is already loaded. Monitoring for other models...")
                another_model_loaded = await monitor_for_other_models(TARGET_MODEL)
                if not another_model_loaded:
                    logger.info(f"No models are loaded now. Loading {TARGET_MODEL}...")
                    await load_model(TARGET_MODEL)
            elif response.get("models", []):
                # Other models are loaded
                latest_expires_at = 0
                for model in response["models"]:
                    expires_at = model.get("expires_at", 0)
                    if expires_at == 0:  # Skip non-expiring models
                        continue
                        
                    expires_at_timestamp = expires_at.timestamp() if isinstance(expires_at, datetime) else expires_at
                    logger.debug(f"Model {model['name']} expires at {datetime.fromtimestamp(expires_at_timestamp)}")
                    if expires_at_timestamp > time.time():
                        latest_expires_at = max(latest_expires_at, expires_at_timestamp)

                if latest_expires_at > 0:
                    logger.info(f"Other models loaded. Waiting for latest expires_at: {datetime.fromtimestamp(latest_expires_at)}")
                    await wait_for_unload(latest_expires_at)
                    
                    # Check again after waiting
                    new_response = await check_loaded_models()
                    if not new_response.get("models", []):
                        logger.info(f"No models are loaded now. Loading {TARGET_MODEL}...")
                        await load_model(TARGET_MODEL)
                    else:
                        remaining_models = [m['name'] for m in new_response['models']]
                        logger.info(f"Models still loaded: {remaining_models}")
                else:
                    logger.info("Only non-expiring models loaded. Waiting 1 minute...")
                    await asyncio.sleep(MONITOR_INTERVAL)
            else:
                # No models are loaded, load target model
                logger.info(f"No models are loaded. Loading {TARGET_MODEL}...")
                await load_model(TARGET_MODEL)

            # Pause before restarting the cycle
            logger.info(f"Cycle complete. Restarting in {CYCLE_INTERVAL} seconds...")
            await asyncio.sleep(CYCLE_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Script stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            logger.info("Retrying in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
