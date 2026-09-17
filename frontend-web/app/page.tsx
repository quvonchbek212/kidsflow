import { redirect } from "next/navigation";

/**
 * Ilova login sahifasidan boshlanadi — marketing landing sahifasi yo'q.
 * Ildiz manzilni `/login` ga yo'naltiramiz, shunda chiqish (logout) va
 * sessiya tugashi kabi barcha yo'llar bitta manzilga olib keladi.
 */
export default function RootPage(): never {
  redirect("/login");
}
