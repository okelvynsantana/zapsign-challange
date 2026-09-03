import { FormControl, FormGroup } from '@angular/forms';

/**
 * The shape of one signer row inside the document form.
 *
 * Naming it keeps `FormArray` typed end to end, so `form.getRawValue().signers` is
 * `{ name, email }[]` rather than `any[]` when it reaches the API client.
 */
export type SignerForm = FormGroup<{
  name: FormControl<string>;
  email: FormControl<string>;
}>;
