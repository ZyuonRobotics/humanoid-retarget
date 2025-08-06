from humanoid_retargeting.motion_player.robot_peroid_player import RobotPeriodPlayer
import click
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "humanoid_retargeting", "motion_player", "robot_sine_config_example.json")

@click.command()
@click.option('--config-file-path', default=DEFAULT_CONFIG_PATH, help='Path to the robot period configuration JSON file.', prompt="Path to the configuration file")
@click.option('--robot-name', default='unitree_g1', help='Name of the robot.', prompt="Name of the robot")
@click.option('--frame-rate', default=100, help='Frame rate for motion generation.')
@click.option('--max-steps', default=300000, help='Maximum number of steps to generate.')
def main(config_file_path, robot_name, frame_rate, max_steps):
    """
    Play periodic robot motion based on JSON configuration.
    
    This script generates and plays sinusoidal motion patterns for robot joints
    based on stepping periods and joint configurations specified in a JSON file.
    """
    # Remove quotes if present
    if config_file_path.startswith('"') or config_file_path.startswith("'"):
        config_file_path = config_file_path[1:-1]
    
    # Check if config file exists
    if not os.path.exists(config_file_path):
        click.echo(f"Error: Configuration file '{config_file_path}' not found.", err=True)
        return
    
    # Create player instance
    player = RobotPeriodPlayer(
        source_file_path=config_file_path,
        robot_name=robot_name,
        frame_rate=frame_rate,
        max_steps=max_steps
    )
    
    # Load motion configuration
    try:
        player.load_motion_file()
        click.echo(f"Successfully loaded configuration from: {config_file_path}")
        click.echo(f"Robot: {robot_name}")
        click.echo(f"Frame rate: {frame_rate} Hz")
        click.echo(f"Max steps: {max_steps}")
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        return
    
    # Play the motion
    click.echo("Starting motion playback...")
    player.render()
        
    # Clean up
    player.close()
    click.echo("Motion playback completed.")


if __name__ == '__main__':
    main() 