from octoprint_autobim.async_command import AsyncCommand, Result


def test_timeout():
	async_command = AsyncCommand()
	async_command._register_result(Result.of(1))

	assert async_command.is_running() is False

	async_command._set_running()

	assert async_command.is_running() is True

	result = async_command._get(0)

	assert result.has_value() is False
	assert result.error is False
	assert result.abort is False
	assert result.value is None
	assert async_command.is_running() is False


def test_multiple_items():
	async_command = AsyncCommand()
	async_command._register_result(Result.of(1))
	async_command._register_result(Result.of(2))
	async_command._register_result(Result.of(3))

	result = async_command._get(0)

	assert result.has_value() is True
	assert result.error is False
	assert result.abort is False
	assert result.value is 3
	assert async_command.is_running() is False

	result = async_command._get(0)

	assert result.has_value() is False
	assert result.error is False
	assert result.abort is False
	assert result.value is None
