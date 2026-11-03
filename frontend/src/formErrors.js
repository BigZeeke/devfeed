/**
 * Turns a failed form request into messages the log-in and sign-up forms can show.
 *
 * DRF answers a bad form with 400 and a body like
 * {"password": ["This password is too short."], "non_field_errors": ["..."]}.
 * Messages for the form's own fields go under those fields; everything else
 * (non_field_errors, detail, unknown keys) becomes one general message.
 */
import { ApiError } from './api.js'

// Returns { fieldErrors: { fieldName: 'message' }, generalMessage: 'message' or null }.
export function describeFormError(error, formFieldNames) {
  if (!(error instanceof ApiError)) {
    // fetch() itself failed: server down, wrong address, or CORS refused.
    return {
      fieldErrors: {},
      generalMessage: 'Could not reach the DevFeed API. Is the backend running?',
    }
  }

  const fieldErrors = {}
  const otherMessages = []
  const responseBody =
    error.responseBody && typeof error.responseBody === 'object' ? error.responseBody : {}

  for (const [errorKey, errorMessages] of Object.entries(responseBody)) {
    // DRF sends a list of messages per key; "detail" is a single string.
    const messageText = Array.isArray(errorMessages)
      ? errorMessages.join(' ')
      : String(errorMessages)
    if (formFieldNames.includes(errorKey)) {
      fieldErrors[errorKey] = messageText
    } else {
      otherMessages.push(messageText)
    }
  }

  // No readable messages at all (for example a 500 page): fall back to the status.
  if (otherMessages.length === 0 && Object.keys(fieldErrors).length === 0) {
    otherMessages.push(error.message)
  }

  return {
    fieldErrors,
    generalMessage: otherMessages.length > 0 ? otherMessages.join(' ') : null,
  }
}
